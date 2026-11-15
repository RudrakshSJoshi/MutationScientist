// design_voice.mjs — craft a DISTINCTIVE, premium "Dr. Mutasci" scientist voice with ElevenLabs
// Voice Design (Creator tier), then import it into Anam and print the Anam voiceId to use.
//
// Requires ELEVENLABS_API_KEY + ANAM_API_KEY in .env (Anam org needs custom-voice access).
// Run once:  node tools/design_voice.mjs            (uses the built-in brief)
//            node tools/design_voice.mjs "your own voice description (20-1000 chars)"
// Then put the printed id in persona.js voiceId (or ANAM_VOICE_ID), and restart.
import "dotenv/config";

const XI = process.env.ELEVENLABS_API_KEY;
const ANAM = process.env.ANAM_API_KEY;
if (!XI) { console.error("ELEVENLABS_API_KEY not set (.env)"); process.exit(1); }
if (!ANAM) { console.error("ANAM_API_KEY not set (.env)"); process.exit(1); }

const BRIEF = process.argv[2] ||
  "A distinguished, warm and authoritative male research scientist in his early fifties. " +
  "Neutral British-influenced English with a measured, documentary-narrator cadence: calm, precise and " +
  "intellectually engaged, with crisp articulation of technical and medical terminology. Trustworthy and " +
  "clear, like a senior investigator explaining a discovery to a smart audience.";
const SAMPLE =
  "The C797S mutation swaps a single cysteine for serine at position 797, removing the covalent anchor that " +
  "osimertinib relies on. In the lab, potency falls from about three nanomolar to several hundred — the " +
  "fingerprint of acquired resistance. A fourth-generation inhibitor like BLU-945 is designed to keep binding.";

const xh = { "xi-api-key": XI, "Content-Type": "application/json" };

async function main() {
  // 1) Voice Design: generate previews from the description.
  console.log("Designing voice previews from brief…");
  let pr = await fetch("https://api.elevenlabs.io/v1/text-to-voice/create-previews", {
    method: "POST", headers: xh,
    body: JSON.stringify({ voice_description: BRIEF, text: SAMPLE }),
  });
  if (!pr.ok) {
    // older endpoint name fallback
    pr = await fetch("https://api.elevenlabs.io/v1/text-to-voice/generate-voice-previews", {
      method: "POST", headers: xh, body: JSON.stringify({ voice_description: BRIEF, text: SAMPLE }) });
  }
  if (!pr.ok) { console.error("Voice Design failed:", pr.status, (await pr.text()).slice(0, 300)); process.exit(1); }
  const previews = (await pr.json()).previews || [];
  if (!previews.length) { console.error("No previews returned"); process.exit(1); }
  const gid = previews[0].generated_voice_id;
  console.log("Got preview generated_voice_id:", gid);

  // 2) Create the permanent ElevenLabs voice from the chosen preview.
  const cr = await fetch("https://api.elevenlabs.io/v1/text-to-voice", {
    method: "POST", headers: xh,
    body: JSON.stringify({ voice_name: "Dr. Mutasci", voice_description: BRIEF, generated_voice_id: gid }),
  });
  if (!cr.ok) { console.error("Create voice failed:", cr.status, (await cr.text()).slice(0, 300)); process.exit(1); }
  const voiceId = (await cr.json()).voice_id;
  console.log("Created ElevenLabs voice_id:", voiceId);

  // 3) Save the key to Anam + import the voice (route C: your own ElevenLabs key).
  const keyRes = await fetch("https://api.anam.ai/v1/voices/elevenlabs-key", {
    method: "PUT", headers: { Authorization: `Bearer ${ANAM}`, "Content-Type": "application/json" },
    body: JSON.stringify({ apiKey: XI }) });
  console.log("Anam elevenlabs-key saved:", keyRes.status);
  const imp = await fetch("https://api.anam.ai/v1/voice-imports", {
    method: "POST", headers: { Authorization: `Bearer ${ANAM}`, "Content-Type": "application/json" },
    body: JSON.stringify({ provider: "ELEVENLABS", providerVoiceId: voiceId, useOrganizationKey: true,
                           displayName: "Dr. Mutasci (designed)" }) });
  const itxt = await imp.text();
  if (!imp.ok) { console.error("Anam import failed:", imp.status, itxt.slice(0, 300)); process.exit(1); }
  let j = {}; try { j = JSON.parse(itxt); } catch {}
  console.log("\n✅ Anam voiceId:", j.id || j.voiceId || "(see response)");
  console.log("   -> set persona.js voiceId to it, or run with ANAM_VOICE_ID=<id>. NOTE: own-key voices need a Cara-4 avatar.");
}
main().catch(e => { console.error(e); process.exit(1); });
