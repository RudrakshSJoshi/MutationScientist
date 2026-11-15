"""
Central configuration for the MutationScientist application.

Nothing here fabricates data. These are display constants, the verified Boltz-2
score convention, and the names of the environment variables that switch a
service from MOCK mode to REAL mode.
"""
from __future__ import annotations
import os
from pathlib import Path

APP_TITLE = "MutationScientist — EGFR Molecular Discovery"
APP_ICON = "🧬"

# ---------------------------------------------------------------------------
# The ONE fact the whole system must agree on — the Boltz-2 affinity convention.
# Verified in molecularinformatics/Boltz2_affinity @ bc06a0b (docs/prediction.md,
# loss/affinity.py): the YAML `value` IS the regression target, no in-code transform.
# ---------------------------------------------------------------------------
BOLTZ_LABEL_UNIT = "log10(IC50_uM)"
SCORE_DEFINITION = (
    "affinity_pred_value is log10(IC50 in micromolar): "
    "log10(IC50_nM) - 3. LOWER = STRONGER binding. This is NOT pIC50. "
    "Anchors: 1 nM -> -3, 1 uM -> 0, 100 uM -> +2. "
    "affinity_probability_binary is a SEPARATE binder-likelihood probability "
    "and must not be conflated with affinity_pred_value."
)

# ---------------------------------------------------------------------------
# Where the data lives. The app searches upward from itself for these, but any
# of them can be pinned with an environment variable.
# ---------------------------------------------------------------------------
DATASET_DIRNAME = "EGFR_RESEARCH_DATASET"
LOADER_FILENAME = "egfr_dataset_loader.py"
ENV_DATASET_ROOT = "EGFR_DATASET_ROOT"   # -> the EGFR_RESEARCH_DATASET folder
ENV_LOADER_PATH = "EGFR_LOADER_PATH"     # -> egfr_dataset_loader.py

# Optional: a REAL Boltz prediction file (JSON) produced by Person 2.
# list[dict] or {complex_id: dict} using the agreed prediction schema.
ENV_BOLTZ_PREDICTIONS = "BOLTZ_PREDICTIONS_PATH"

# Optional: the fine-tuned MutationScientist LLM (Person 1 / Adaption).
# The served fine-tuned model is called via Adaption's RESPONSES API and is
# referenced as "stack:<slug>", where the stack is created in the Adaption web
# UI after training. If ADAPTION_API_KEY + ADAPTION_STACK are set, llm_service
# attempts the real call; otherwise it uses the grounded template report and
# labels it as such.
ENV_ADAPTION_API_KEY = "ADAPTION_API_KEY"
ENV_ADAPTION_STACK = "ADAPTION_STACK"        # the fine-tuned stack slug -> model="stack:<slug>"
ENV_ADAPTION_MODEL = "ADAPTION_MODEL_ID"     # legacy alias; used as the stack slug if ADAPTION_STACK is unset
ENV_ADAPTION_BASE_URL = "ADAPTION_BASE_URL"  # default https://api.prod.adaptionlabs.ai
ADAPTION_DEFAULT_BASE_URL = "https://api.prod.adaptionlabs.ai"

# Optional: a LIVE evidence-retrieval API (Person 3 / Terminal 5). When set,
# EvidenceService queries it (GET {url}?mutation_id=&compound_id=&match=) and
# falls back to the curated+cited local evidence on any error. Until it is set,
# the app serves the real curated evidence that ships with the dataset.
ENV_EVIDENCE_API_URL = "EVIDENCE_API_URL"

# Optional: a GENERIC OpenAI-compatible endpoint (e.g. a hosted fine-tuned model).
# If ALL THREE are set, llm_service attempts the real call against this endpoint;
# otherwise it uses the grounded template report and labels it as such. The
# Adaption pair above takes precedence when both are configured.
ENV_OPENAI_BASE_URL = "OPENAI_BASE_URL"  # e.g. https://my-endpoint/v1
ENV_OPENAI_API_KEY = "OPENAI_API_KEY"
ENV_OPENAI_MODEL = "OPENAI_MODEL"

# ---------------------------------------------------------------------------
# The fine-tuned MutationScientist model identity + its measured Adaption
# win-rate journey.
#
# Win-rate = Adaption AutoScientist's head-to-head metric vs the base model
# (0.50 = ties base; higher = beats base). These are REAL training-run results
# and are shown as the MODEL's benchmark — never as a scientific (biochemical)
# measurement. Provenance tier = REASONED (the LLM), never MEASURED.
#
#   v1 raw baseline   Qwen3.5-4B · 1,126 rows · no augmentation → 0.3617 (lost to base)
#   v3 best fine-tune gemma-3-4b · ~20k domain-aug rows (Adaptive-Data) → 0.78
# ---------------------------------------------------------------------------
MODEL_PRODUCT = "MutationScientist"   # the served product/endpoint identity (stable)
MODEL_NAME = "gemma-3-4b"             # the leaderboard-winning fine-tune (benchmark below)
MODEL_LABEL = "MutationScientist · gemma-3-4b"
MODEL_ENDPOINT = "http://localhost:8000/v1"   # OpenAI-compatible gateway (stable name below)
MODEL_ENDPOINT_MODEL = "mutationscientist"    # gateway's stable model name; survives hot-swaps
WINRATE_BEST = 0.78           # best Adaption win-rate — gemma-3-4b fine-tune (v3)
WINRATE_BASELINE = 0.3617     # v1 raw baseline — Qwen3.5-4B, 1,126 rows, no augmentation
WINRATE_TIES_BASE = 0.50      # by definition a model ties its own base at 0.50
WINRATE_SOURCE = (
    "Adaption AutoScientist head-to-head win-rate vs the base model "
    "(0.50 = ties base; higher = better). Real training-run result — the model's "
    "benchmark, not a biochemical measurement."
)
# The journey shown on the Overview (baseline → best). Stage, win-rate, note.
WINRATE_JOURNEY = [
    ("Base model", 0.50, "ties its own base by definition"),
    ("v1 · raw SFT", 0.3617, "Qwen3.5-4B · 1,126 rows · no augmentation (lost to base)"),
    ("v3 · augmented", 0.78, "gemma-3-4b · ~20k domain-aug rows (Adaptive-Data) — the lever"),
]

APP_DIR = Path(__file__).resolve().parent.parent


def env(name: str, default: str | None = None) -> str | None:
    v = os.environ.get(name)
    return v if v else default


def is_covalent(status: str | None) -> bool:
    """True only for covalent inhibitors.

    The naive test ``"coval" in status.lower()`` is WRONG: it matches
    'non-covalent' too (the substring 'coval' is inside it), which would flag
    every reversible inhibitor as covalent. This guards against that.
    """
    s = (status or "").strip().lower()
    return "coval" in s and not s.startswith("non")
