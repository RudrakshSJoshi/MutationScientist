// list_voices.mjs — browse Anam's voice catalogue to pick a premium voiceId for the persona.
// Reads ANAM_API_KEY from .env (never printed). Usage:
//   node tools/list_voices.mjs [search] [gender male|female] [country GB|US...]
// e.g. node tools/list_voices.mjs "narration" male GB
import "dotenv/config";

const key = process.env.ANAM_API_KEY;
if (!key) { console.error("ANAM_API_KEY not set (.env)"); process.exit(1); }

const [search, gender, country] = process.argv.slice(2);
const u = new URL("https://api.anam.ai/v1/voices");
u.searchParams.set("perPage", "20");
if (search) u.searchParams.set("search", search);
if (gender) u.searchParams.set("gender", gender);
if (country) u.searchParams.set("country", country);

const r = await fetch(u, { headers: { Authorization: `Bearer ${key}` } });
if (!r.ok) { console.error("HTTP", r.status, (await r.text()).slice(0, 200)); process.exit(1); }
const j = await r.json();
for (const v of j.data || []) {
  console.log(`${(v.gender||"?")[0]} ${v.country||"--"} zdr=${v.isZdr?1:0}  ${v.displayName}  [${v.id}]  ${(v.description||"").slice(0,80)}`);
}
console.log(`-- total ${j.meta?.total ?? j.meta?.totalItems ?? "?"} (page ${j.meta?.page ?? 1})`);
