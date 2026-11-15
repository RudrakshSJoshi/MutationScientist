// model.js — server-side bridge to OUR MutationScientist model.
// Keeps all model/Adaption credentials on the server; the browser only ever talks to /api/chat-stream.
//
// Two backends, selected by env (see .env.example):
//   1) OpenAI-compatible endpoint (e.g. local vLLM serving the Qwen3.5-4B + MutationScientist LoRA):
//        MODEL_BASE_URL=http://localhost:8000/v1   [MODEL_API_KEY] [MODEL_NAME]
//      -> POST {base}/chat/completions  (stream:true, SSE)  — true token streaming.
//   2) Adaption Inference Stack (Responses API — NOT OpenAI /chat/completions):
//        ADAPTION_STACK=<slug>  ADAPTION_API_KEY=pt_live_...  [ADAPTION_BASE_URL]
//      -> POST {base}/api/v1/responses {model:"stack:<slug>", input, instructions} -> output_text
//         (not token-streamed; we chunk the final text by sentence so lip-sync stays lively).
//
// If MODEL_BASE_URL is set it wins; else if ADAPTION_STACK is set we use Adaption; else we
// default to a local OpenAI endpoint at http://localhost:8000/v1 (the "another terminal is
// standing it up" path), so the common case needs zero config.

const MODEL_BASE_URL = process.env.MODEL_BASE_URL?.replace(/\/$/, "");
const MODEL_API_KEY = process.env.MODEL_API_KEY; // optional for local vLLM / MLX
let MODEL_NAME = process.env.MODEL_NAME;         // optional; auto-discovered if absent
const MODEL_MAX_TOKENS = Number(process.env.MODEL_MAX_TOKENS || 512);
// Qwen3 is a "thinking" model: by default it streams chain-of-thought (delta.reasoning) before the
// answer, which wastes the token budget and delays the first spoken word. Disable it so the avatar
// speaks the answer directly and promptly. Set MODEL_ENABLE_THINKING=1 to turn it back on.
const ENABLE_THINKING = process.env.MODEL_ENABLE_THINKING === "1";

const ADAPTION_STACK = process.env.ADAPTION_STACK;
const ADAPTION_API_KEY = process.env.ADAPTION_API_KEY;
const ADAPTION_BASE_URL = (process.env.ADAPTION_BASE_URL || "https://api.prod.adaptionlabs.ai").replace(/\/$/, "");

const DEFAULT_OPENAI_BASE = "http://localhost:8000/v1";

export function backendInfo() {
  if (MODEL_BASE_URL) return { kind: "openai", detail: MODEL_BASE_URL };
  if (ADAPTION_STACK && ADAPTION_API_KEY) return { kind: "adaption", detail: `stack:${ADAPTION_STACK}` };
  return { kind: "openai", detail: `${DEFAULT_OPENAI_BASE} (default)` };
}

// Resolve (and cache) which concrete model will actually answer — handy for /api/health & demos.
export async function resolvedModel() {
  const { kind } = backendInfo();
  if (kind === "adaption") return `stack:${ADAPTION_STACK}`;
  try { return (await resolveOpenAI()).model; } catch { return MODEL_NAME || "unresolved"; }
}

// Resolve the OpenAI base + model name (auto-discover the model id from /models if not pinned).
async function resolveOpenAI() {
  const base = MODEL_BASE_URL || DEFAULT_OPENAI_BASE;
  const headers = { "Content-Type": "application/json" };
  if (MODEL_API_KEY) headers["Authorization"] = `Bearer ${MODEL_API_KEY}`;
  if (!MODEL_NAME) {
    try {
      const r = await fetch(`${base}/models`, { headers });
      if (r.ok) {
        const j = await r.json();
        const ids = (j?.data || []).map((m) => m.id).filter(Boolean);
        // Prefer OUR fine-tune if the server also lists base/other models; else take the first.
        MODEL_NAME = ids.find((id) => /egfr|mutationscientist|mlx_model/i.test(id)) || ids[0];
      }
    } catch { /* fall through; MODEL_NAME may stay undefined */ }
  }
  return { base, headers, model: MODEL_NAME || "default" };
}

// ---- OpenAI-compatible streaming (SSE) --------------------------------------
async function* streamOpenAI(messages) {
  const { base, headers, model } = await resolveOpenAI();
  const body = {
    model, messages, stream: true, temperature: 0.3, max_tokens: MODEL_MAX_TOKENS,
  };
  // Turn off Qwen3 thinking so we stream the answer (delta.content) directly, not reasoning.
  if (!ENABLE_THINKING) body.chat_template_kwargs = { enable_thinking: false };
  const r = await fetch(`${base}/chat/completions`, {
    method: "POST",
    headers,
    body: JSON.stringify(body),
  });
  if (!r.ok || !r.body) {
    const detail = await r.text().catch(() => "");
    throw new Error(`model endpoint ${r.status}: ${detail.slice(0, 300)}`);
  }
  const decoder = new TextDecoder();
  let buf = "";
  for await (const chunk of r.body) {
    buf += decoder.decode(chunk, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const line of lines) {
      const s = line.trim();
      if (!s || !s.startsWith("data:")) continue;
      const payload = s.slice(5).trim();
      if (payload === "[DONE]") return;
      try {
        const j = JSON.parse(payload);
        const tok = j?.choices?.[0]?.delta?.content;
        if (tok) yield tok;
      } catch { /* ignore keepalive / partial lines */ }
    }
  }
}

// ---- Adaption Responses API (non-streaming -> sentence chunks) --------------
function* chunkBySentence(text) {
  // Split on sentence boundaries so the avatar starts speaking sooner and lip-sync stays natural.
  const parts = text.match(/[^.!?]+[.!?]+(\s|$)|[^.!?]+$/g) || [text];
  for (const p of parts) { const t = p.trim(); if (t) yield t + " "; }
}

async function* streamAdaption(messages) {
  const system = messages.find((m) => m.role === "system")?.content || "";
  const convo = messages.filter((m) => m.role !== "system");
  const r = await fetch(`${ADAPTION_BASE_URL}/api/v1/responses`, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Authorization": `Bearer ${ADAPTION_API_KEY}` },
    body: JSON.stringify({
      model: `stack:${ADAPTION_STACK}`,
      instructions: system,
      // Pass the conversation as OpenAI-Responses-style input; fall back handled by the stack.
      input: convo.map((m) => ({ role: m.role, content: m.content })),
    }),
  });
  const text = await r.text();
  if (!r.ok) throw new Error(`adaption ${r.status}: ${text.slice(0, 300)}`);
  let out = "";
  try {
    const j = JSON.parse(text);
    out = j.output_text
      || j?.output?.map?.((o) => o?.content?.map?.((c) => c?.text).filter(Boolean).join("")).join("")
      || "";
  } catch { out = text; }
  out = (out || "").trim();
  if (!out) throw new Error("adaption returned empty output_text");
  yield* chunkBySentence(out);
}

// Streaming stripper for reasoning markup: removes <think>…</think> blocks and stray think tags,
// so the avatar never speaks chain-of-thought even if the model emits it. Holds back a tiny tail so
// a tag split across chunks is still caught.
function makeThinkStripper() {
  let carry = "";
  let inThink = false;
  const OPEN = "<think>", CLOSE = "</think>";
  return {
    push(text) {
      carry += text;
      let out = "";
      while (true) {
        if (inThink) {
          const e = carry.indexOf(CLOSE);
          if (e === -1) { carry = carry.slice(-7); return out; } // keep possible partial close tag
          carry = carry.slice(e + CLOSE.length); inThink = false;
        } else {
          const o = carry.indexOf(OPEN);
          const c = carry.indexOf(CLOSE);
          if (c !== -1 && (o === -1 || c < o)) { out += carry.slice(0, c); carry = carry.slice(c + CLOSE.length); continue; }
          if (o !== -1) { out += carry.slice(0, o); carry = carry.slice(o + OPEN.length); inThink = true; continue; }
          // no full tag; emit all but a short tail that could be the start of one
          if (carry.length > 8) { out += carry.slice(0, carry.length - 8); carry = carry.slice(-8); }
          return out;
        }
      }
    },
    flush() { const o = inThink ? "" : carry.replace(/<\/?think>/g, ""); carry = ""; return o; },
  };
}

// Public: async generator of text chunks for the given chat messages (system already included).
export async function* generate(messages) {
  const { kind } = backendInfo();
  const src = kind === "adaption" ? streamAdaption(messages) : streamOpenAI(messages);
  const strip = makeThinkStripper();
  for await (const chunk of src) {
    const cleaned = strip.push(chunk);
    if (cleaned) yield cleaned;
  }
  const tail = strip.flush();
  if (tail) yield tail;
}
