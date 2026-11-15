// record_demo.mjs — record a backup video of Dr. Mutasci nailing the two hero stories.
// Drives the live :3000 UI with Playwright (headed, for reliable WebRTC) and captures the avatar +
// prediction cards + streamed grounded answers for C797S×osimertinib then L858R/C797S×BLU-945.
//
// NOTE: Playwright page video is SILENT (no audio). For an audio capture, screen-record with QuickTime
// while clicking "Play 90-sec pitch" (see README). This gives the visual backup autonomously.
//
// Usage (server must be running on :3000, model reachable):  node tools/record_demo.mjs
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";

import { fileURLToPath } from "node:url";
const TARGET = process.env.DEMO_URL || "http://localhost:3000";
const OUT = fileURLToPath(new URL("../demo/", import.meta.url));
mkdirSync(OUT, { recursive: true });

const HEROES = ["osimertinib_resistance", "blu945_prediction"];
const DWELL_MS = 26000;   // hold on each story so the avatar is seen speaking it
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function run(headless) {
  const browser = await chromium.launch({
    headless,
    args: ["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream",
           "--autoplay-policy=no-user-gesture-required"],
  });
  const ctx = await browser.newContext({
    viewport: { width: 1280, height: 800 },
    permissions: ["microphone"],
    recordVideo: { dir: OUT, size: { width: 1280, height: 800 } },
  });
  const page = await ctx.newPage();
  page.on("console", m => { if (m.type() === "error") console.log("[page error]", m.text()); });

  console.log(`Loading ${TARGET} (headless=${headless})…`);
  await page.goto(TARGET, { waitUntil: "networkidle" });
  await page.click("#startBtn");

  // wait until live (Stop button enabled)
  await page.waitForFunction(() => !document.getElementById("stopBtn").disabled, { timeout: 45000 });
  console.log("Avatar live. Greeting…");
  await sleep(7000); // let the greeting play

  for (const key of HEROES) {
    console.log("Story:", key);
    await page.click(`.hero[data-key="${key}"]`);
    // wait for a grounded answer to start streaming
    await page.waitForFunction(() => {
      const a = document.getElementById("answer");
      return a && a.style.display !== "none" && a.textContent.trim().length > 40;
    }, { timeout: 60000 }).catch(() => console.log("  (answer wait timed out; continuing)"));
    await sleep(DWELL_MS); // let the avatar speak the story on camera
  }

  console.log("Wrapping up…");
  await page.click("#stopBtn").catch(() => {});
  await sleep(1500);
  const video = page.video();
  await ctx.close();          // finalizes the video file
  await browser.close();
  const path = video ? await video.path() : null;
  console.log("VIDEO:", path);
  return path;
}

(async () => {
  try {
    await run(false);         // headed first (WebRTC reliable)
  } catch (e) {
    console.log("Headed run failed:", e.message, "\nRetrying headless…");
    await run(true);
  }
})();
