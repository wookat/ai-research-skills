"""Autonomous audit → fix → re-audit loop, scoped to ONE run.

Every run gets its own isolated COPY of the skill scripts under
`<outdir>/_skill_run_copy/`. The code-fixer subagent only edits files
inside that copy. The shipped skill (`skills/html2pptx/scripts/`) is
NEVER touched — so per-run patches don't leak into other posters or
other people's installations.

Why: vision audit findings are often poster-specific. A fix that helps
poster A might regress poster B. Per-run isolation gives you fearless
iteration on a single poster without polluting the global skill.

The skill copy has its own internal git repo (one initial commit) so
we can rollback per-round changes with `git checkout`. The COPY's git
has no relation to the outer repo's git.

Pipeline per round:
  1. build + render + vision_audit (via the copy, PYTHONPATH-overridden)
  2. pick highest-severity actionable issue not yet attempted
  3. spawn `claude -p` subagent (constrained: --add-dir <copy>, only
     Read/Edit/Grep/Glob — no Bash, no git, can't escape the copy)
  4. rebuild + re-audit
  5. if issue count dropped → keep (commit in copy's git)
     otherwise → rollback (copy's `git checkout` on file)

Final artifact: `<outdir>/_skill_run_copy_diff.patch` — the cumulative
diff vs baseline. Inspect it manually; if a fix is genuinely general
(not poster-specific), cherry-pick into the shipped skill via a normal
PR. Otherwise the patch stays scoped to this run only.

Usage:
  python -m scripts.auto_fix_loop \\
      --html /path/poster.html \\
      --outdir /tmp/fix_loop_run/ \\
      --max-rounds 3
"""
from __future__ import annotations
import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

THIS = Path(__file__).resolve().parent
SKILL_DIR = THIS.parent          # skills/html2pptx/
SKILL_SCRIPTS = SKILL_DIR / "scripts"

# Categories vision tends to false-positive on. Whitelist what we'll act on.
ACTIONABLE_CATEGORIES = {
    "missing_element", "extra_element", "text_clipped",
    "wrap_mismatch", "font_substitution", "z_order",
    # excluded: alignment_off, color_drift, spacing_off, size_mismatch,
    #          position_shift, other
}


def setup_run_copy(outdir: Path) -> Path:
    """Copy skill scripts into <outdir>/_skill_run_copy/scripts/ and
    init a per-copy git repo (for clean rollback). Returns copy root."""
    copy_dir = outdir / "_skill_run_copy"
    if copy_dir.exists():
        shutil.rmtree(copy_dir)
    copy_scripts = copy_dir / "scripts"
    # Copy all .py files + GOTCHAS.md (subagent reads it). Skip __pycache__.
    shutil.copytree(SKILL_SCRIPTS, copy_scripts,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    # Also copy GOTCHAS.md + difference.md so subagent can reference them
    for doc in ("GOTCHAS.md", "difference.md", "SKILL.md"):
        src = SKILL_DIR / doc
        if src.exists():
            shutil.copy(src, copy_dir / doc)
    # Per-copy git for rollback isolation
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=copy_dir, check=True)
    subprocess.run(["git", "-c", "user.email=fix-loop@local",
                    "-c", "user.name=fix-loop",
                    "add", "."], cwd=copy_dir, check=True)
    subprocess.run(["git", "-c", "user.email=fix-loop@local",
                    "-c", "user.name=fix-loop",
                    "commit", "-q", "-m", "baseline"], cwd=copy_dir, check=True)
    return copy_dir


def copy_git(*args, copy_dir: Path) -> str:
    """Run git inside the per-copy repo."""
    r = subprocess.run(["git", "-c", "user.email=fix-loop@local",
                        "-c", "user.name=fix-loop", *args],
                       cwd=copy_dir, capture_output=True, text=True, check=True)
    return r.stdout.strip()


def build_and_audit_via_copy(copy_dir: Path, html: Path,
                              outdir: Path, name: str,
                              vision_model: str) -> dict | None:
    """Run the build via the per-run copy. CWD = copy_dir so `python -m
    scripts.auto_correct_loop` resolves to the COPY's scripts package."""
    cmd = ["python", "-m", "scripts.auto_correct_loop",
           "--html", str(html), "--outdir", str(outdir), "--name", name,
           "--vision-model", vision_model]
    print(f"\n  [build+audit via copy] cwd={copy_dir.name}  vision-model={vision_model}",
          file=sys.stderr)
    proc = subprocess.run(cmd, cwd=copy_dir,
                          capture_output=True, text=True, timeout=300)
    if proc.returncode != 0:
        print(f"  [build+audit] FAILED rc={proc.returncode}", file=sys.stderr)
        print(proc.stderr[-2000:], file=sys.stderr)
        return None
    audit_path = outdir / f"{name}_audit.json"
    if not audit_path.exists():
        print(f"  [build+audit] no audit produced (auth missing?)", file=sys.stderr)
        return None
    return json.loads(audit_path.read_text())


def pick_top_issue(audit: dict, tried_ids: set[str]) -> dict | None:
    sev_order = {"high": 0, "medium": 1, "low": 2}
    issues = sorted(audit.get("issues", []),
                    key=lambda i: (sev_order.get(i["severity"], 9), i["category"]))
    for it in issues:
        if it["category"] not in ACTIONABLE_CATEGORIES:
            continue
        iid = f"{it['category']}::{it.get('where','')[:60]}"
        if iid in tried_ids:
            continue
        return it
    return None


def issue_id(issue: dict) -> str:
    return f"{issue['category']}::{issue.get('where','')[:60]}"


def spawn_fixer(issue: dict, copy_dir: Path, round_num: int,
                fix_model: str) -> bool:
    """Spawn `claude -p` to fix this issue in the COPY's html_to_pptx.py.
    Subagent is sandboxed via --add-dir <copy_dir>; it cannot edit files
    outside the copy. Returns True if subagent made any edit."""
    prompt = f"""You are fixing a visual-fidelity bug in an isolated COPY
of the html2pptx skill at `{copy_dir}`. You are NOT editing the shipped
skill — only this copy. So your fix can be poster-specific (the outer
loop is iterating on ONE poster).

The Claude vision auditor compared the HTML render (ground truth) to the
PPT render and found this issue:

- **Severity:** {issue['severity']}
- **Category:** {issue['category']}
- **Where:** {issue['where']}
- **Description:** {issue['description']}
- **Block index (if any):** {issue.get('block_idx')}

**Your task:** find the root cause in `scripts/html_to_pptx.py` (and/or
the embedded JS DOM extractor in that file) and make a MINIMAL fix. The
HTML is correct truth; the bug is in our extraction or rendering layer.

Read `GOTCHAS.md` (in the same dir) first — many fixes follow a pattern
documented there (G15: img decoration tile, G17: ::before/::after, etc.).

**Constraints:**
- Edit ONLY `scripts/html_to_pptx.py`. If you think another file is
  needed, STOP and explain instead of editing it.
- Make the SMALLEST possible diff. Don't refactor, rename, or add
  features beyond fixing this exact issue.
- Add ONE short comment explaining WHY (cite the auditor finding briefly).
- Do NOT run the build/audit yourself — the outer loop will do that.
- If you can't identify a clear root cause in ~5 minutes of reading,
  STOP and emit "GIVE_UP: <reason>" as your last line — don't guess-edit.

When done, output a one-sentence summary of what you changed."""

    prompt_file = copy_dir / f".fix_prompt_round_{round_num}.txt"
    prompt_file.write_text(prompt)
    # Subagent constrained to the copy dir; Bash/git deliberately excluded.
    # Pass --model explicitly so behavior is reproducible across users
    # (otherwise inherits whatever the user's claude CLI is configured with).
    cmd = [
        "claude", "-p",
        "--model", fix_model,
        "--allowedTools", "Read", "Edit", "Grep", "Glob",
        "--add-dir", str(copy_dir),
    ]
    print(f"\n  [fixer] spawning claude -p (model={fix_model}, "
          f"sandboxed to {copy_dir.name})...", file=sys.stderr)
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, cwd=copy_dir,
                              input=prompt_file.read_text(),
                              capture_output=True, text=True, timeout=600)
    except subprocess.TimeoutExpired:
        print(f"  [fixer] TIMEOUT after 600s", file=sys.stderr)
        prompt_file.unlink(missing_ok=True)
        return False
    elapsed = time.time() - t0
    prompt_file.unlink(missing_ok=True)

    print(f"  [fixer] returned rc={proc.returncode} in {elapsed:.1f}s",
          file=sys.stderr)
    tail = "\n".join(proc.stdout.strip().splitlines()[-15:])
    print(f"  [fixer output tail]\n{tail}", file=sys.stderr)
    if "GIVE_UP" in proc.stdout:
        return False
    if proc.returncode != 0:
        print(f"  [fixer stderr tail]\n{proc.stderr[-500:]}", file=sys.stderr)
        return False
    return True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, type=Path)
    ap.add_argument("--outdir", type=Path, default=None,
                    help="Output directory. Defaults to ./output/<UTC_timestamp>/ "
                         "so each run is isolated.")
    ap.add_argument("--name", default="poster")
    ap.add_argument("--max-rounds", type=int, default=3)
    ap.add_argument("--max-give-up-streak", type=int, default=2)
    ap.add_argument("--fix-model", default="claude-opus-4-8",
                    help="Model used by the `claude -p` subagent that proposes "
                         "code fixes. Default Opus 4.8 (best reasoning for "
                         "root-causing across the JS DOM extractor + Python "
                         "renderer). Override with claude-sonnet-4-6 for "
                         "cheaper but less reliable fixes.")
    ap.add_argument("--vision-model", default="claude-opus-4-8",
                    help="Model passed through to vision_audit for the "
                         "per-round fidelity check. Default Opus 4.8.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print the fixer prompt for each round but don't call it.")
    a = ap.parse_args()

    if a.outdir is None:
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        a.outdir = Path("./output") / ts
        print(f"[outdir] defaulting to {a.outdir.resolve()}", file=sys.stderr)
    a.outdir = a.outdir.resolve()  # absolute — copy uses different cwd

    a.outdir.mkdir(parents=True, exist_ok=True)
    copy_dir = setup_run_copy(a.outdir)
    print(f"[fix-loop] isolated skill copy at {copy_dir}", file=sys.stderr)
    print(f"           (your shipped {SKILL_DIR} stays untouched)", file=sys.stderr)
    print(f"[fix-loop] models: vision-audit={a.vision_model}, fixer={a.fix_model}",
          file=sys.stderr)

    tried_ids: set[str] = set()
    history: list[dict] = []
    give_up_streak = 0

    # Round 0: baseline
    audit = build_and_audit_via_copy(copy_dir, a.html, a.outdir, a.name,
                                      vision_model=a.vision_model)
    if not audit:
        sys.exit("baseline audit failed")
    print(f"\n[round 0] baseline: {audit['n_issues']} issues "
          f"(h{audit['by_severity'].get('high',0)} "
          f"m{audit['by_severity'].get('medium',0)})", file=sys.stderr)
    history.append({"round": 0, "n": audit["n_issues"],
                    "by_severity": audit["by_severity"],
                    "action": "baseline"})

    for r in range(1, a.max_rounds + 1):
        issue = pick_top_issue(audit, tried_ids)
        if issue is None:
            print(f"\n[round {r}] no actionable issues left — done", file=sys.stderr)
            break
        iid = issue_id(issue)
        tried_ids.add(iid)
        print(f"\n[round {r}] targeting: [{issue['severity']}] "
              f"{issue['category']} @ {issue['where'][:80]}", file=sys.stderr)
        print(f"            {issue['description'][:160]}", file=sys.stderr)

        if a.dry_run:
            print(f"[round {r}] --dry-run: skipping fixer call", file=sys.stderr)
            break

        sha_before = copy_git("rev-parse", "HEAD", copy_dir=copy_dir)
        ok = spawn_fixer(issue, copy_dir, round_num=r, fix_model=a.fix_model)
        if not ok:
            print(f"[round {r}] fixer gave up — moving on", file=sys.stderr)
            give_up_streak += 1
            if give_up_streak >= a.max_give_up_streak:
                print(f"[round {r}] {give_up_streak} consecutive failures — stopping",
                      file=sys.stderr)
                break
            continue
        give_up_streak = 0

        diff_stat = copy_git("diff", "--stat", sha_before, copy_dir=copy_dir)
        if not diff_stat.strip():
            print(f"[round {r}] fixer ran but produced no diff", file=sys.stderr)
            continue
        print(f"  [diff]\n{diff_stat}", file=sys.stderr)

        new_audit = build_and_audit_via_copy(copy_dir, a.html, a.outdir, a.name,
                                              vision_model=a.vision_model)
        if not new_audit:
            print(f"[round {r}] post-fix audit failed — reverting", file=sys.stderr)
            copy_git("reset", "--hard", sha_before, copy_dir=copy_dir)
            continue

        old_h = audit["by_severity"].get("high", 0)
        new_h = new_audit["by_severity"].get("high", 0)
        old_n = audit["n_issues"]
        new_n = new_audit["n_issues"]
        improved = (new_h < old_h) or (new_h == old_h and new_n < old_n)
        action = "KEEP" if improved else "REVERT"
        print(f"\n[round {r}] before: {old_n} (h{old_h})  →  "
              f"after: {new_n} (h{new_h})  →  {action}", file=sys.stderr)

        if improved:
            # Commit accepted change in the copy's git
            copy_git("-c", "user.email=fix-loop@local",
                     "-c", "user.name=fix-loop",
                     "add", ".", copy_dir=copy_dir)
            copy_git("-c", "user.email=fix-loop@local",
                     "-c", "user.name=fix-loop",
                     "commit", "-q", "-m",
                     f"round {r}: {issue['category']} @ {issue['where'][:50]}",
                     copy_dir=copy_dir)
            audit = new_audit
            history.append({"round": r, "n": new_n,
                            "by_severity": new_audit["by_severity"],
                            "action": "kept", "issue": iid})
        else:
            copy_git("reset", "--hard", sha_before, copy_dir=copy_dir)
            history.append({"round": r, "n": old_n,
                            "by_severity": audit["by_severity"],
                            "action": "reverted", "issue": iid})

    # Export final cumulative diff for human review
    diff_path = a.outdir / f"{a.name}_run_patches.diff"
    baseline_sha = copy_git("rev-list", "--max-parents=0", "HEAD", copy_dir=copy_dir)
    diff = copy_git("diff", baseline_sha, "HEAD", copy_dir=copy_dir)
    diff_path.write_text(diff)

    summary_path = a.outdir / f"{a.name}_fix_loop_summary.json"
    summary_path.write_text(json.dumps({
        "max_rounds": a.max_rounds,
        "tried_issues": sorted(tried_ids),
        "history": history,
        "skill_copy": str(copy_dir),
        "diff_patch": str(diff_path),
        "note": ("Patches are scoped to this run only. The shipped skill at "
                 f"{SKILL_DIR} was not modified. Review the .diff file; if "
                 "any fix is genuinely general, cherry-pick into the shipped "
                 "skill via a normal PR. Otherwise patches stay here."),
    }, indent=2))
    print(f"\n[fix-loop] summary:")
    for h in history:
        print(f"  round {h['round']:>2}: {h['n']:>3d} issues  ({h['action']})",
              file=sys.stderr)
    print(f"\n  summary:     {summary_path}", file=sys.stderr)
    print(f"  cumulative diff (review me):  {diff_path}", file=sys.stderr)
    print(f"  skill copy (kept for re-runs): {copy_dir}", file=sys.stderr)


if __name__ == "__main__":
    main()
