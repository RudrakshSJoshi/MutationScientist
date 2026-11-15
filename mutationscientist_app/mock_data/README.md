# mock_data/

Mock records that let the interface be demonstrated before real model outputs
exist. **Mock data is always labelled in the UI** (red ⚠️ MOCK badges, banners)
and is never shown as a real prediction or measurement.

- **Boltz predictions** are generated *on the fly* by `services/boltz_service.py`
  as deterministic placeholders (`model_checkpoint="MOCK_PLACEHOLDER"`,
  `is_mock=True`). `boltz_predictions.sample.json` below shows the exact schema
  Person 2 should deliver.
- **Evidence** is NOT mocked — the Evidence Explorer serves the real curated,
  cited evidence from `EGFR_RESEARCH_DATASET/curated/biological_evidence.csv`.
- **LLM report** is a grounded TEMPLATE until the fine-tuned model is wired in;
  it restates only values present in the dataset context.

## Going live (no UI changes needed)
| Component | Owner | Switch |
|---|---|---|
| Boltz predictions | Person 2 | set `BOLTZ_PREDICTIONS_PATH=/path/to/predictions.json` |
| MutationScientist LLM | Person 1 | set `ADAPTION_API_KEY` + `ADAPTION_MODEL_ID` (opt. `ADAPTION_BASE_URL`) |
| Evidence API | Person 3 | already real; swap `EvidenceService` for the live API if desired |
