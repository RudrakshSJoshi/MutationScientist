// import_voice.mjs — OPTIONAL: give Dr. Mutasci a specific ElevenLabs voice (Creator tier).
//
// The default persona voice is already a premium, ElevenLabs-backed Anam stock voice, so you only
// need this to use a particular ElevenLabs Voice Library / Creator voice. It imports that voice into
// your Anam org and prints the Anam voiceId to put in persona.js (or ANAM_VOICE_ID).
// Requires Anam custom-voice access on your org (else Anam returns an access error -> contact Anam).
//
// Three routes (see Anam docs /personas/voices/custom-voices):
//   A) Public Voice-Library id, on Anam's ElevenLabs account (ZDR-safe):
//        node tools/import_voice.mjs --id <elevenLabsVoiceId> [--model eleven_v3_conversational] [--name "Dr Mutasci"]
//   B) Share link (Professional Voice Clone shared "anyone with the link"):
//        node tools/import_voice.mjs --share "https://elevenlabs.io/app/voice-lab/share/.../..." [--name ...]
//   C) Your OWN ElevenLabs key (instant clones / Voice Design; billed to you; NOT ZDR; needs Cara-4):
//        ELEVENLABS_API_KEY=... node tools/import_voice.mjs --id <voiceId> --own [--model ...] [--name ...]
import "dotenv/config";

const key = process.env.ANAM_API_KEY;
if (!key) { console.error("ANAM_API_KEY not set (.env)"); process.exit(1); }
const args = Object.fromEntries(process.argv.slice(2).reduce((a, v, i, arr) => {
  if (v.startsWith("--")) a.push([v.slice(2), arr[i + 1]?.startsWith("--") || arr[i + 1] === undefined ? true : arr[i + 1]]);
  return a;
}, []));
const H = (extra = {}) => ({ Authorization: `Bearer ${key}`, "Content-Type": "application/json", ...extra });

async function main() {
  if (args.own) {
    const elk = process.env.ELEVENLABS_API_KEY;
    if (!elk) { console.error("--own requires ELEVENLABS_API_KEY in .env"); process.exit(1); }
    const r = await fetch("https://api.anam.ai/v1/voices/elevenlabs-key", {
      method: "PUT", headers: H(), body: JSON.stringify({ apiKey: elk }),
    });
    console.log("save elevenlabs-key:", r.status, r.ok ? "ok" : (await r.text()).slice(0, 200));
    if (!r.ok) process.exit(1);
  }
  const body = { provider: "ELEVENLABS", displayName: args.name || "Dr. Mutasci" };
  if (args.share) body.shareUrl = args.share;
  else if (args.id) { body.providerVoiceId = args.id; if (args.own) body.useOrganizationKey = true; }
  else { console.error("need --id <voiceId> or --share <url>"); process.exit(1); }
  if (args.model) body.providerModelId = args.model;

  const r = await fetch("https://api.anam.ai/v1/voice-imports", {
    method: "POST", headers: H(), body: JSON.stringify(body),
  });
  const txt = await r.text();
  if (!r.ok) { console.error("voice-import failed:", r.status, txt.slice(0, 300)); process.exit(1); }
  let j = {}; try { j = JSON.parse(txt); } catch {}
  console.log("Imported voice. Anam voiceId:", j.id || j.voiceId || "(see response)", "\n", txt.slice(0, 300));
  console.log("\n-> set persona.js voiceId to that id, or run with ANAM_VOICE_ID=<id>");
}
main();
