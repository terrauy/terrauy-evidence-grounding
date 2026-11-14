"""TEGB command-line tools: run a model on the benchmark, score it, package and validate a submission.

    python -m tegb --help

Standard library only. The scoring code is the frozen v0.1 harness (`harness/detect.py`, `harness/evaluate.py`);
this package adds a provider-agnostic way to produce responses and a reproducible submission format.
"""

BENCHMARK_VERSION = "v0.1"
TOOLS_VERSION = "0.1.1"
SUBMISSION_SCHEMA = "tegb-submission/1"
