# MutationScientist — real-time Anam avatar (EGFR resistance), driven by our fine-tuned model

**Dr. Mutasci** is a real-time [Anam](https://anam.ai) avatar that *speaks* the EGFR inhibitor-resistance
story (NSCLC) and answers from **our fine-tuned MutationScientist model**, grounded in the real
`EGFR_RESEARCH_DATASET` — real measurements, cited evidence, and **real Boltz-2 predictions**. It never
invents numbers: everything it says traces to a structured context assembled from the dataset.

Hackathon track: Voice, Vision & Generative Media (Anam + ElevenLabs + our model).

## What makes it a showstopper
- **BYO-LLM (client-side):** the avatar's persona uses `llmId: "CUSTOMER_CLIENT_V1"`, so Anam's built-in
  LLM is OFF. The browser streams **our model's** tokens to the avatar. Keys stay server-side.
- **Grounded in real data:** pick a mutation × inhibitor and the server feeds the model the exact
  structured context the research app uses (mutation record + compound + **real Boltz-2 prediction** +
  cited evidence + measurements). The on-screen card shows the actual prediction the avatar interprets.
- **Two hero stories:**
  - **C797S × osimertinib** (resistance): covalent → *no* Boltz complex, so the avatar honestly says
    "no prediction" and reasons from the measured **574 nM vs 2.82 nM baseline (~200× loss)** (Melis 2026).
  - **L858R/C797S × BLU-945** (real prediction): Boltz-2 **−2.01 log₁₀µM (≈9.8 nM)** vs measured
    **6.32 nM** — a genuine prediction-vs-experiment pair on screen.
- **Premium voice:** a studio-grade British Anam voice (ElevenLabs-backed, ZDR-safe). Swap in your own
  ElevenLabs Creator voice with `tools/import_voice.mjs`.
- **90-second auto-pitch:** one button walks the avatar through intro → resistance → real prediction → why
  grounding matters, all answered live by the grounded model.

## Architecture
```
browser (public/)
  ├─ POST /api/session-token ─> server.js ─Bearer ANAM key─> api.anam.ai   -> sessionToken (NOT the key)
  ├─ createClient(token) → streamToVideoElement("persona-video")           (WebRTC video+audio)
  ├─ pick a hero pair → GET /api/contexts → render the real prediction CARD + set active contextKey
  └─ user speaks / types / hero → POST /api/chat-stream {messages, contextKey} ─> server.js
        → system = no-fabrication prompt + the pair's STRUCTURED CONTEXT (single system message)
        → OUR model (model.js): local OpenAI-compatible endpoint (MLX/vLLM) or Adaption Responses API
        ← NDJSON {"content":"…"} (think-tags stripped) → talkStream.streamMessageChunk → avatar speaks
```
- **No key ever leaves the server** — not Anam, not the model/Adaption key.
- **Grounding** is a single merged system message (the model server requires one system message first).
- **Grounding guard (critical):** the raw model hallucinates specifics without context (it once placed
  C797S at "position 179"). The server NEVER calls it ungrounded — a selected pair uses that pack; any
  other question falls back to a dataset-level **"general"** context (full mutation panel with correct
  notations + compounds + score definition); with no context it refuses. With context it says "position 797".
- **Think-stripping:** Qwen3 thinking is disabled and any stray `<think>…</think>` is removed server-side,
  so the avatar never speaks chain-of-thought.

## Run it
```bash
cd anam-explainer
npm install
cp .env.example .env            # put ANAM_API_KEY in .env (gitignored)
# Our model must be reachable: a local OpenAI-compatible server at http://localhost:8000/v1
#   (MLX/vLLM serving Qwen3.5-4B + the MutationScientist LoRA), OR set ADAPTION_STACK + ADAPTION_API_KEY.
npm start
# open http://localhost:3000 → "Start the explainer" → allow mic
# → click a hero pair (card appears) or ask: "How does C797S affect osimertinib binding,
#   and what does the Boltz prediction say?" → the avatar answers from our model, grounded.
# → or click "Play 90-sec pitch".
```
`GET /api/health` shows the resolved model + loaded contexts. Requires Node ≥ 18.

## Files
| file | what it does |
|---|---|
| `server.js` | Express: `/api/session-token` (mint), `/api/chat-stream` (grounded proxy), `/api/contexts`, `/api/health`. |
| `model.js` | Bridge to OUR model: OpenAI-compatible (streaming) or Adaption Responses API; model auto-pick; think-stripper. |
| `persona.js` | `SYSTEM_PROMPT` (grounding + no-fabrication rules), `GREETING`, `PERSONA_CONFIG` (`CUSTOMER_CLIENT_V1`, premium voiceId). |
| `data/contexts.json` | The grounded hero packs (real mutation/compound/Boltz/evidence) — self-contained; no secrets. |
| `public/index.html` + `public/app.js` | Demo UI: video stage, hero buttons, live prediction card, ask box, 90-sec pitch, client-side BYO loop. |
| `tools/build_grounding.py` | Regenerates `data/contexts.json` (+ "general" fallback pack) + the consolidated real `boltz_predictions.json`. |
| `tools/list_voices.mjs` | Browse Anam voices to pick a `voiceId`. |
| `tools/import_voice.mjs` | Import a specific ElevenLabs voice (by id / share link) into your Anam org. |
| `tools/design_voice.mjs` | **Craft** a distinctive Dr. Mutasci voice via ElevenLabs Voice Design (Creator), then import to Anam. |
| `tools/serve_forever.sh` | Overnight watchdog: keeps `:3000` up, restarts on crash (logs to `tools/serve_forever.log`). |
| `tools/record_demo.mjs` | Playwright: records a backup video of the avatar nailing both hero stories (silent — see below). |

## Run it all night
```bash
bash tools/serve_forever.sh &     # keeps http://localhost:3000 up, auto-restarts on crash
```
The server degrades gracefully if the model endpoint drops (honest "can't reach my model" line), and recovers
automatically when it returns. Keep Terminal 1's model server (`:8000`) up for live answers.

## Voice (ElevenLabs Creator)
Default: a premium British studio voice (Anam stock voices are ElevenLabs-backed, ZDR-safe). To craft a
**bespoke** Dr. Mutasci voice: add `ELEVENLABS_API_KEY` to `.env`, then
`node tools/design_voice.mjs` (ElevenLabs Voice Design → imports to Anam → prints the `voiceId`). Put that id
in `persona.js` or `ANAM_VOICE_ID`. (Own-key voices need a Cara-4 avatar.) Or import an existing voice with
`tools/import_voice.mjs`.

## Backup video
`node tools/record_demo.mjs` drives the live UI and records `demo/*.webm` (+ `.mp4`) of both hero stories —
**silent** (Playwright can't capture the WebRTC audio). For an **audio** backup, screen-record with QuickTime
(File → New Screen Recording, pick system audio) while clicking **"Play 90-sec pitch"**. `demo/` is gitignored.

## Regenerating the grounding
`data/contexts.json` is built from the local research stack (not committed): the `EGFR_RESEARCH_DATASET`,
`~/Desktop/application/services/*`, and the Boltz run at `~/Desktop/EGFR_TRAINING/boltz_run`.
```bash
python3 tools/build_grounding.py   # rewrites data/contexts.json + ~/Desktop/EGFR_TRAINING/boltz_predictions.json
```
Every value traces to the dataset or the Boltz run — nothing is fabricated. The Boltz affinity convention
is `log10(IC50 µM)`, lower = stronger (NOT pIC50); IC50-nM equivalents are pre-computed into the context so
the avatar quotes correct potencies.

## Voice
Default: **Alexander Kensington — Studio Quality** (Anam voiceId `9c39154a-…`), British, ElevenLabs-backed,
ZDR-safe. Browse others: `node tools/list_voices.mjs narration male GB`. Override at runtime with
`ANAM_VOICE_ID`. To use your own ElevenLabs Creator voice, see `tools/import_voice.mjs` (needs Anam
custom-voice org access).

## Secret hygiene
`ANAM_API_KEY` (and any `ELEVENLABS_API_KEY` / Adaption key) live ONLY in `.env` (gitignored, chmod 600).
No key is in code, in `public/`, or committed. **Rotate the Anam key after the event** (it was shared in chat).

## Not for clinical decisions
Biochemical potency ≠ cellular or clinical response; the avatar says so. Predictions are computational.
