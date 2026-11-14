# EGFR MutationScientist — Adaption AutoScientist fine-tune (Person 1)

Pushes the MutationScientist SFT dataset to **Adaption AutoScientist** and runs a
**Qwen/Qwen3.5-4B** supervised fine-tune (SFT, LoRA). Dataset source =
`EGFR_RESEARCH_DATASET/mutation_scientist/` (sft_train + sft_validation).

## Status (launched 2026-11-14)
| Item | Value |
|---|---|
| Dataset on Adaption | `8db28bbb-1c2e-418e-889c-b1c465f95935` (raw, **1,126 rows**, status `succeeded`) |
| Fine-tune run | `1cc9e20f-4cdb-45cb-9491-7e7ac4bdd8f4` (status `running`) |
| Base model | `Qwen/Qwen3.5-4B` (SFT / instruction, LoRA) |
| Config | max_iterations 3, target_win_rate 0.7 |

## Why train+val (1,126) not train (912)
Adaption's SFT floor is **1,000 rows**. `sft_train` alone is 912, so we upload
`sft_train + sft_validation` (1,126, built into `sft_train_plus_val.csv`) and keep
`sft_test` (215) + `eval_questions.jsonl` as an untouched external eval.

## Why "raw" processing (not "adapt")
`processing_mode: "raw"` trains on our already-grounded prompt/completion rows
**as-is** — no augmentation, no rewriting of the scientifically-verified
completions. (`adapt` mode would spend extra credits and let the platform rewrite
our rows, which we do not want for curated scientific data.)

## The working API flow (what `adaption_finetune.py` does)
1. `POST /api/v1/datasets` with `{"source":{name, file_format:"csv", processing_mode:"raw", column_mapping:{prompt,completion}}}` → `dataset_id` + presigned `upload_instructions.url`
2. `PUT` the CSV to the presigned URL (no bearer header)
3. `POST /api/v1/datasets/{id}/upload/complete` `{s3_key, file_size_bytes}` → triggers processing
4. poll `GET /api/v1/datasets/{id}/status` until `succeeded` (row_count set)
5. `POST /api/v1/autoscientist` `{dataset_id, model, training_method:"instruction"}`
   — **no column_mapping** here (raw datasets bake it in at create; re-sending is rejected)

## Monitor / download
```bash
set -a; . ./.adaption_key; set +a            # loads ADAPTION_API_KEY (gitignored)
# status:
curl -s -H "Authorization: Bearer $ADAPTION_API_KEY" \
  https://api.prod.adaptionlabs.ai/api/v1/autoscientist/1cc9e20f-4cdb-45cb-9491-7e7ac4bdd8f4 | python3 -m json.tool
# when status=succeeded, download the best adapter/artifact:
curl -s -H "Authorization: Bearer $ADAPTION_API_KEY" -L \
  https://api.prod.adaptionlabs.ai/api/v1/autoscientist/1cc9e20f-4cdb-45cb-9491-7e7ac4bdd8f4/download -o best_model.zip
```
Or re-run `python3 adaption_finetune.py --poll` after setting the run id, and watch in the Adaption web app.

## Files
- `adaption_finetune.py` — end-to-end push + launch (`--dry-run`, `--check-models`, `--upload-only`, `--yes`, `--dataset-id`)
- `sft_train_plus_val.csv` — the 1,126-row upload (train+val), 0 empty prompt/completion
- `.adaption_key` — **chmod 600, gitignored, never commit.** Holds the API key.

## 🔐 Secret hygiene
The API key lives only in `.adaption_key`. It was shared in chat, so **rotate it**
in Adaption → Settings → API keys after the hackathon.

## Caveats
- 1,240 of the 1,341 LLM rows are teacher-generated + machine-checked, **not**
  human-reviewed — a domain-expert pass is still recommended.
- SFT ≠ guaranteed quality; evaluate against `sft_test` + `eval_questions.jsonl`
  (held out from training) before trusting outputs. Not for clinical decisions.
