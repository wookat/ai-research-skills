# Research Integrity Red Lines

These rules protect the evidence chain from accidental or deliberate
post-hoc improvement:

- Do not change metrics, dataset splits, or evaluation protocol after seeing
  results in order to make a claim look stronger. Any protocol change is
  recorded and triggers a full rerun.
- Do not delete failed experiments, inconvenient slices, or negative results.
  Preserve them in the hypothesis tree and results archive with their
  attribution.
- Do not self-review in the same context that generated or modified the
  object. Verdicts require a fresh context, preferably a different model;
  otherwise label the likely score inflation.
- Do not refresh verdicts on a wall-clock schedule. A review is rerun only
  after the reviewed object changes; objective experiment loops may use
  machine-checkable stop conditions.

Broader research-misconduct red lines (referenced by `paper-writing`,
`citation-audit`, `paper-verification`, `thesis-convert`, `dataset-curation`,
and the automatic loops):

- **Fabrication / falsification**: never invent, extrapolate, or "smooth"
  data points, metrics, or experiment logs; every reported number traces to
  an on-disk artifact. Never fabricate citations or BibTeX from memory.
- **Plagiarism and unattributed reuse**: quoted or closely paraphrased text,
  reused figures, and reused code must be attributed; self-plagiarism of
  prior publications follows the venue's/institution's reuse policy and is
  disclosed.
- **Authorship responsibility**: authorship implies accountability for the
  content. LLMs/agents are not authors; a human must be able to defend every
  claim, number, and citation in the submission.
- **AI/LLM usage disclosure**: follow the target venue's / institution's
  policy on disclosing AI assistance (writing, coding, analysis). When a
  disclosure section exists, fill it truthfully; never instruct a model to
  hide AI involvement where disclosure is required.
- **Dataset licensing and data governance**: verify each dataset's license
  permits the intended use (training, redistribution, commercial use);
  respect privacy constraints (PII, de-identification) and cite dataset
  sources per their terms.
- **Ethics / human-subject concerns**: work involving human subjects,
  personal data, or dual-use risk follows the applicable IRB/ethics-review
  requirements and the venue's ethics checklist; flag, don't bury, potential
  harms.

When in doubt, preserve the raw artifact, document the deviation, and make
the smallest defensible claim supported by the unchanged evidence.
