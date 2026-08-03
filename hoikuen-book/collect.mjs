// はいチーズ！ノート 収集スクリプト（自分のアカウントのデータを自分用に保存する目的）
//
// 使い方:
//   node collect.mjs
//
// ブラウザが開くので、自分でログインして連絡帳を1日ずつ表示していくだけ。
// 表示したページのHTML・スクリーンショット・写真画像が data/ に自動保存される。
// 終わったらターミナルで Ctrl+C。
//
// ログインID・パスワードはこのスクリプトには一切渡さない（画面で自分で入力する）。

import { chromium } from 'playwright';
import { createHash } from 'node:crypto';
import { mkdirSync, writeFileSync, appendFileSync } from 'node:fs';
import path from 'node:path';

const OUT = path.resolve('data');
const PAGES = path.join(OUT, 'pages');
const IMAGES = path.join(OUT, 'images');
for (const d of [OUT, PAGES, IMAGES]) mkdirSync(d, { recursive: true });

const seenPages = new Set();
const seenImages = new Set();
const hash = (buf) => createHash('sha256').update(buf).digest('hex').slice(0, 16);
const log = (entry) =>
  appendFileSync(
    path.join(OUT, 'log.jsonl'),
    JSON.stringify({ time: new Date().toISOString(), ...entry }) + '\n'
  );

const browser = await chromium.launch({ headless: false });
const context = await browser.newContext({ viewport: { width: 1280, height: 900 } });
const page = await context.newPage();

// 表示中に読み込まれた画像を自動保存（アイコン等の小さい画像は除外）
context.on('response', async (res) => {
  try {
    const ct = res.headers()['content-type'] ?? '';
    if (!ct.startsWith('image/')) return;
    const body = await res.body();
    if (body.length < 30_000) return;
    const h = hash(body);
    if (seenImages.has(h)) return;
    seenImages.add(h);
    const ext = ct.includes('png') ? 'png' : ct.includes('webp') ? 'webp' : 'jpg';
    writeFileSync(path.join(IMAGES, `${h}.${ext}`), body);
    log({ type: 'image', file: `${h}.${ext}`, url: res.url(), bytes: body.length });
    console.log(`📷 写真を保存しました (${Math.round(body.length / 1024)}KB)`);
  } catch {
    /* 読み取れないレスポンスは無視 */
  }
});

console.log('----------------------------------------------------------');
console.log('ブラウザが開きます。はいチーズ！ノートにログインしてください。');
console.log('ログイン後、連絡帳を1日ずつ順番に表示していくだけでOKです。');
console.log('表示したページと写真は自動で data/ に保存されます。');
console.log('終わったらこのターミナルで Ctrl+C を押してください。');
console.log('----------------------------------------------------------');

await page.goto('https://8122.jp/');

// 2秒ごとに画面の内容をチェックし、変化があればHTMLとスクショを保存
setInterval(async () => {
  try {
    const html = await page.content();
    const h = hash(Buffer.from(html));
    if (seenPages.has(h)) return;
    seenPages.add(h);
    const stamp = Date.now();
    writeFileSync(path.join(PAGES, `${stamp}-${h}.html`), html);
    await page.screenshot({ path: path.join(PAGES, `${stamp}-${h}.png`), fullPage: true });
    log({ type: 'page', file: `${stamp}-${h}.html`, url: page.url() });
    console.log(`📝 ページを保存: ${page.url()}`);
  } catch {
    /* 遷移中などで取得できない瞬間は無視 */
  }
}, 2000);
