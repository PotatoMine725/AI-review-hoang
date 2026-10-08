const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const base = process.env.TEST_BASE_URL || 'http://localhost:3000';

async function traverse(page, delta, accept) {
  const handled = new Promise(resolve => page.once('dialog', async dialog => {
    assert.match(dialog.message(), /chưa lưu/);
    if (accept) await dialog.accept(); else await dialog.dismiss();
    resolve();
  }));
  await page.evaluate(delta => history.go(delta), delta);
  await handled;
}

(async () => {
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  try {
    const page = await browser.newPage();
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/merchant/products');
    await page.locator('tr').filter({ hasText: 'Notion' }).getByRole('link', { name: 'Review PKB' }).click();
    await page.waitForURL('**/merchant/products/notion');
    const detailUrl = page.url();
    const historyLength = await page.evaluate(() => history.length);
    const description = page.getByLabel('Mô tả sản phẩm', { exact: true });
    await description.fill('Unsaved PKB description');
    // Repeated cancellations restore the original entry without remounting or
    // inserting extra history entries. Saving then allows Back with no prompt.
    for (let i = 0; i < 2; i++) {
      await traverse(page, -1, false);
      await page.waitForURL(detailUrl);
      assert.equal(await description.inputValue(), 'Unsaved PKB description');
      assert.equal(await page.evaluate(() => history.length), historyLength);
    }
    await page.getByRole('button', { name: 'Lưu draft', exact: true }).click();
    await page.getByText('Đã lưu draft trong trình duyệt.', { exact: true }).waitFor();
    let cleanDialogs = 0;
    const unexpected = async dialog => { cleanDialogs++; await dialog.dismiss(); };
    page.on('dialog', unexpected);
    await page.goBack(); await page.waitForURL('**/merchant/products');
    await page.goForward(); await page.waitForURL(detailUrl);
    page.off('dialog', unexpected);
    assert.equal(cleanDialogs, 0, 'saved edits must not block history');
    assert.equal(await description.inputValue(), 'Unsaved PKB description');
    await description.fill('Discard this revision');
    await traverse(page, -1, true); await page.waitForURL('**/merchant/products');
    // Create an existing forward destination, then check Forward protection too.
    await page.goForward(); await page.waitForURL(detailUrl);
    await page.getByRole('button', { name: 'Gửi review', exact: true }).click();
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Merchant duyệt PKB', exact: true }).click();
    await page.getByRole('link', { name: 'Mở Content Factory' }).click();
    await page.getByRole('button', { name: 'Tạo template', exact: true }).click();
    await page.getByRole('link', { name: /Review PKB/ }).click();
    await page.getByRole('button', { name: 'Tạo draft mới', exact: true }).click();
    await page.goBack(); await page.waitForURL('**/merchant/content');
    await page.getByRole('tab', { name: 'Kịch bản', exact: true }).click();
    const script = page.getByRole('textbox', { name: 'Chỉnh sửa Kịch bản', exact: true });
    await script.fill('Unsaved content script');
    for (const delta of [1, -1]) {
      await traverse(page, delta, false);
      await page.waitForURL('**/merchant/content');
      assert.equal(await script.inputValue(), 'Unsaved content script');
    }
    await traverse(page, 1, true); await page.waitForURL('**/merchant/products/notion');
    assert.deepEqual(errors, []);
    console.log('PASS: Back/Forward cancellation preserves PKB/content edits and history length; confirmation proceeds; saved edits navigate without prompts.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
