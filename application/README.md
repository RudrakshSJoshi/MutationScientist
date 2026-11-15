# MutationScientist research report

From the repository root, use Python 3.10+ with SQLite FTS5 to build the local index from the repository dataset and start the app.

```sh
python3 -m scientific_evidence.retriever.build
python3 -m application.app
```

Open [MutationScientist on localhost](http://127.0.0.1:8765/) and enter a research question. For a JSON report from the terminal, run:

```sh
python3 -m application.app 'Why does gefitinib lose potency against T790M?'
```

The local summary uses the SQLite index. It reports exact-pair experimental measurement coverage and shows each result with its assay type, genotype, compound and clickable source. It supports comparisons of up to three EGFR profiles and two inhibitors. It filters explicitly numbered NCI-H1975 clones and single-condition enzyme requests for 1 mmol/L ATP or ATP Km. Try asking why osimertinib loses potency against C797S to see how the report labels experiments on related profiles.

## Graph keyword search

Use **Search graph** in the web app or run one of these commands:

```sh
python3 -m application.app --graph 'P00533'
python3 -m application.app --graph 'ERBB1 T790M gefitinib' --exact-only --assay-type biochemical_binding
python3 -m application.app --graph 'EGFR PDB 6LUD'
```

The protein search covers human EGFR and recognizes EGFR, ERBB1, HER1, P00533 and the full protein name. A protein-only search exposes links to indexed variants, inhibitors and assay types. Recognized entity types narrow the same evidence record, and remaining keywords match indexed text. Single-variant searches also follow the recorded membership of combined profiles. Results preserve the actual genotype and label those records as related. An explicit profile matches that profile.

Graph results offer **Exact variants only**, assay, ATP condition, and cell line or clone filters. For example, filter for `NCI-H1975 clone 2` or choose the `1 mmol/L ATP` enzyme condition. Click a node in an evidence card to browse it, narrow to its assay, or open the source. The observation and citation stay visible on the card.

Use `scientific_evidence.evidence_api.search_graph(keywords, exact_only=False, assay_type=None, cell_line=None, atp_condition=None, limit=15, offset=0)` to get matched nodes, evidence-linked edges, and the source records as JSON-compatible data. The graph reads the existing SQLite index. A new checkout can build the index with `python3 -m scientific_evidence.retriever.build`.

## Connect the model

Set `MUTATIONSCIENTIST_LLM_URL` to the complete inference endpoint and `MUTATIONSCIENTIST_LLM_MODEL` to the served checkpoint or model ID. Set `MUTATIONSCIENTIST_LLM_API_KEY` when the endpoint requires a bearer token.

| Environment variable | Example or accepted values |
| --- | --- |
| `MUTATIONSCIENTIST_LLM_URL` | `http://127.0.0.1:8000/v1/chat/completions` |
| `MUTATIONSCIENTIST_LLM_MODEL` | The ID configured by the model owner |
| `MUTATIONSCIENTIST_LLM_PROTOCOL` | `chat` (default) or `responses` |
| `MUTATIONSCIENTIST_LLM_API_KEY` | Optional bearer token |

For an Adaption-hosted model or stack, use the `responses` protocol and the `/api/v1/responses` inference endpoint. The app sends the question and a bounded evidence packet to the configured endpoint. [Adaption Responses API](https://docs.adaptionlabs.ai/api/resources/responses/methods/create)

The model selects and orders evidence IDs in a JSON object. The app validates them against the supplied packet and renders statements from the source records, preserving assay labels, precise values, bounds and genotype scope. Invalid model replies and endpoint failures fall back to a labeled local summary. The app can also compute documented ratios from source-matched enzyme or cellular measurements and convert a supplied Boltz-2 score to its nominal concentration scale.

For embedding in another application, call `application.services.evidence_service.answer_question(question, generate=...)`. The optional `generate` callable receives a list of role/content messages and returns selection JSON as text. The established structured entry point remains `scientific_evidence.evidence_api.retrieve_evidence()`.

## Verification

```sh
python3 -m unittest discover -s application/tests -v
python3 -m scientific_evidence.evaluation.graph_benchmark
```

The tests submit raw questions against the real SQLite index, check citation visibility and scope, and exercise both model response formats. They use controlled model responses. A live scientific quality comparison awaits the model owner's endpoint.
