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

When in doubt, preserve the raw artifact, document the deviation, and make
the smallest defensible claim supported by the unchanged evidence.
