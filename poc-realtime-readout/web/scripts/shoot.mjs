// 빌드한 화면을 날짜별로 헤드리스 캡처하고, 콘솔 오류·가로 넘침·재생 동작을 확인한다.
// 사용: npm run build && npx vite preview  (다른 터미널)  →  node scripts/shoot.mjs [outDir] [baseUrl]
// 크로미움 경로가 다르면 PW_CHROMIUM=/path/to/chrome 로 지정.
import { chromium } from "playwright-core";
import { mkdirSync } from "node:fs";

const out = process.argv[2] ?? "shots";
const base = process.argv[3] ?? "http://127.0.0.1:4173/";
mkdirSync(out, { recursive: true });

const browser = await chromium.launch({ headless: true, executablePath: process.env.PW_CHROMIUM || undefined });
const errors = [];
const shots = [
  ["desk-0228", 1440, 900, "2026-02-28", "light"], ["desk-0311", 1440, 900, "2026-03-11", "light"],
  ["desk-0322-dark", 1440, 900, "2026-03-22", "dark"], ["phone-0309", 390, 844, "2026-03-09", "light"],
];
for (const [name, w, h, d, scheme] of shots) {
  const page = await browser.newPage({ viewport: { width: w, height: h }, colorScheme: scheme });
  page.on("pageerror", (e) => errors.push(`${name}: ${e.message}`));
  // 외부 폰트 로드 실패는 네트워크 문제라 제외
  page.on("console", (m) => m.type() === "error" && !m.text().startsWith("Failed to load resource") && errors.push(`${name}: ${m.text()}`));
  await page.goto(`${base}#d=${d}`, { waitUntil: "networkidle" });
  await page.waitForSelector(".quad");
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  if (overflow > 0) errors.push(`${name}: 가로 스크롤 ${overflow}px`);
  await page.screenshot({ path: `${out}/${name}.png`, fullPage: true });
  await page.close();
}
// 재생 버튼: 3초 뒤 날짜가 넘어갔는지
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
await page.goto(`${base}#d=2026-03-01`, { waitUntil: "networkidle" });
const before = await page.textContent(".tb-day");
await page.click(".play");
await page.waitForTimeout(3000);
const after = await page.textContent(".tb-day");
if (before === after) errors.push(`재생: 날짜가 안 넘어감 (${before})`);
else console.log(`재생 확인: ${before} → ${after}`);
await browser.close();
console.log(errors.length ? errors.join("\n") : "오류 없음");
process.exit(errors.length ? 1 : 0);
