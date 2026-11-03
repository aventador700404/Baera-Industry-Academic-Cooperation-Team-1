// 빌드한 화면을 판독 시점별로 헤드리스 캡처하고, 콘솔 오류를 모아 보여준다.
// 사용: npm run build && npx vite preview  (다른 터미널)  →  node scripts/shoot.mjs [outDir] [baseUrl]
// 크로미움 경로가 다르면 PW_CHROMIUM=/path/to/chrome 로 지정.
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://127.0.0.1:4173/";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ headless: true, executablePath: process.env.PW_CHROMIUM || undefined });
const errors = [];
for (const [name, w, h, view, scheme] of [
  ["desk-w1", 1440, 900, "w1", "light"], ["desk-w2", 1440, 900, "w2", "light"], ["desk-w5-dark", 1440, 900, "w5", "dark"],
  ["phone-w3", 390, 844, "w3", "light"],
]) {
  const page = await browser.newPage({ viewport: { width: w, height: h }, colorScheme: scheme });
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
  // 외부 폰트 로드 실패는 네트워크 문제라 경고로만
  page.on("console", (m) => m.type() === "error" && !m.text().startsWith("Failed to load resource") && errors.push(`${name}: ${m.text()}`));
  await page.goto(`${base}#view=${view}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".card");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (overflow > 0) errors.push(`${name}: 가로 스크롤 ${overflow}px`);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: true });
  await page.close();
}
await browser.close();
console.log(errors.length ? errors.join("\n") : "오류 없음");
process.exit(errors.length ? 1 : 0);
