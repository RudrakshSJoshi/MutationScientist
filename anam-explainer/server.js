// server.js — minimal Express server for the Anam explainer.
// SECURITY: the Anam API key stays here on the server. The browser only ever receives a
// short-lived session token. Never ship ANAM_API_KEY to the client.
import "dotenv/config";
import express from "express";
import { readFileSync } from "node:fs";
import { PERSONA_CONFIG, SYSTEM_PROMPT } from "./persona.js";
import { generate, backendInfo, resolvedModel } from "./model.js";

const app = express();
app.use(express.json());
app.use(express.static("public"));

// Grounded context packs (one per hero pair) — real mutation/compound/Boltz/evidence, built by
// tools/build_grounding.py from the EGFR dataset. The avatar is grounded in exactly these.
let CONTEXTS = {};
try {
  CONTEXTS = JSON.parse(readFileSync(new URL("./data/contexts.json", import.meta.url)));
} catch (e) {
  console.warn("[!] data/contexts.json not loaded — grounding disabled:", e.message);
}

const ANAM_API_KEY = process.env.ANAM_API_KEY;
const ANAM_TOKEN_URL = "https://api.anam.ai/v1/auth/session-token";

if (!ANAM_API_KEY) {
  console.warn("\n[!] ANAM_API_KEY is not set. Create anam-explainer/.env with:  ANAM_API_KEY=your_key_here\n");
}

// Mint a short-lived Anam session token for the browser.
app.post("/api/session-token", async (_req, res) => {
  if (!ANAM_API_KEY) return res.status(500).json({ error: "Server missing ANAM_API_KEY" });
  try {
    const r = await fetch(ANAM_TOKEN_URL, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${ANAM_API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        personaConfig: PERSONA_CONFIG,
        expiresInSeconds: 900,   // 15 min is plenty for a demo turn
        maxSessions: 3,
      }),
    });
    const text = await r.text();
    if (!r.ok) {
      console.error("Anam token error", r.status, text);
      return res.status(r.status).json({ error: "Anam token request failed", status: r.status, detail: text });
    }
    const data = JSON.parse(text);
    // Anam returns { sessionToken: "<jwt>" } — forward ONLY that to the browser.
    return res.json({ sessionToken: data.sessionToken });
  } catch (e) {
    console.error(e);
    return res.status(500).json({ error: String(e) });
  }
});

// Health/diagnostics: which model backend is wired, without leaking any secret.
app.get("/api/health", async (_req, res) => {
  res.json({ ok: true, anamKey: Boolean(ANAM_API_KEY), model: backendInfo(),
             resolvedModel: await resolvedModel(), contexts: Object.keys(CONTEXTS) });
});

// The hero pairs for the UI: key, title, question, and the on-screen prediction card (no heavy context).
app.get("/api/contexts", (_req, res) => {
  const list = Object.entries(CONTEXTS).map(([key, p]) => ({
    key, title: p.title, question: p.question, card: p.card,
    mutation_id: p.mutation_id, compound_id: p.compound_id,
  }));
  res.json({ contexts: list });
});

// Client-side BYO-LLM proxy. The browser (CUSTOMER_CLIENT_V1) sends the chat history here; we
// prepend the grounded SYSTEM_PROMPT, call OUR MutationScientist model, and stream the answer back
// as newline-delimited JSON ({"content":"..."} per line). No model/Adaption key ever reaches the
// browser. The browser forwards each chunk to the avatar via talkStream.streamMessageChunk(...).
app.post("/api/chat-stream", async (req, res) => {
  const incoming = Array.isArray(req.body?.messages) ? req.body.messages : [];
  // Keep only clean {role, content} pairs; map Anam's "persona" role to "assistant".
  const history = incoming
    .filter((m) => m && typeof m.content === "string" && m.content.trim())
    .map((m) => ({ role: m.role === "user" ? "user" : "assistant", content: m.content }));

  // Inject the grounded structured context for the selected hero pair (source of truth for numbers).
  // NOTE: the model server requires a SINGLE system message at the start, so prompt + context are
  // merged into one system message (not two).
  const pack = req.body?.contextKey ? CONTEXTS[req.body.contextKey] : null;
  let systemContent = SYSTEM_PROMPT;
  if (pack?.context) {
    systemContent +=
      "\n\n=== STRUCTURED CONTEXT (the ONLY source of truth for numbers, mechanisms and citations; " +
      "if a value is not here, do not state it) ===\n" + JSON.stringify(pack.context);
  }
  const messages = [{ role: "system", content: systemContent }, ...history];

  res.setHeader("Content-Type", "application/x-ndjson; charset=utf-8");
  res.setHeader("Cache-Control", "no-cache");
  try {
    let any = false;
    for await (const chunk of generate(messages)) {
      any = true;
      res.write(JSON.stringify({ content: chunk }) + "\n");
    }
    if (!any) res.write(JSON.stringify({ content: "Sorry, I didn't get a response from my model that time." }) + "\n");
  } catch (e) {
    console.error("chat-stream error:", e?.message || e);
    // Speak a short, honest fallback instead of silence (never fabricate science here).
    res.write(JSON.stringify({ content: "Sorry, I'm having trouble reaching my model right now." }) + "\n");
    res.write(JSON.stringify({ error: String(e?.message || e) }) + "\n");
  } finally {
    res.end();
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  const b = backendInfo();
  console.log(`EGFR Anam explainer -> http://localhost:${PORT}`);
  console.log(`  model backend: ${b.kind} (${b.detail})`);
});
