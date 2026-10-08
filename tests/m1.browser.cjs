const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const base = process.env.TEST_BASE_URL || 'http://localhost:3000';
const output = process.env.TEST_OUTPUT_DIR || path.resolve('test-results');
const key = 'reviewlab.m1.mock.v2';

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ headless: true, ...(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH } : {}) });
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } });
    const errors = []; page.on('pageerror', error => errors.push(error.message));
    await page.goto(base + '/products');
    await page.getByRole('button', { name: 'Thêm sản phẩm', exact: true }).waitFor();
    await page.getByLabel('Website URL').fill('http://www.demo.example/tool-a/');
    await page.getByLabel('Merchant affiliate URL').fill('https://demo.example/?ref=test');
    await page.getByRole('button', { name: 'Thêm sản phẩm', exact: true }).click();
    await page.waitForURL('**/products/*'); const productUrl = page.url();
    await page.getByRole('heading', { name: 'Chưa có PKB' }).waitFor();
    await page.reload(); await page.getByRole('button', { name: 'Bắt đầu job mock' }).waitFor();
    await page.getByRole('button', { name: 'Bắt đầu job mock' }).click();
    await page.getByRole('button', { name: 'Mô phỏng lỗi crawl' }).click();
    await page.reload(); await page.getByRole('button', { name: 'Thử lại job mock' }).waitFor();
    await page.getByRole('button', { name: 'Thử lại job mock' }).click();
    await page.getByRole('button', { name: 'Hoàn tất job mock' }).click();
    await page.getByLabel('Mô tả sản phẩm', { exact: true }).waitFor();
    assert.match(await page.getByLabel('Mô tả sản phẩm', { exact: true }).inputValue(), /English-language/);
    assert.ok(await page.getByLabel('Giá niêm yết', { exact: true }).isVisible());
    assert.ok(await page.getByText('AI suy luận (mock)', { exact: true }).first().isVisible());

    await page.getByLabel('Mô tả sản phẩm', { exact: true }).fill('A merchant-edited English product description.');
    assert.ok(await page.getByRole('button', { name: 'Gửi review', exact: true }).isDisabled());
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('link', { name: /Danh sách sản phẩm/ }).click();
    assert.equal(page.url(), productUrl, 'unsaved changes prevent navigation when cancelled');
    assert.equal(await page.getByLabel('Mô tả sản phẩm', { exact: true }).inputValue(), 'A merchant-edited English product description.');

    // Persistence failure must retain the edited form and not claim success.
    await page.evaluate((key) => {
      const original = Storage.prototype.setItem;
      Storage.prototype.setItem = function (k, v) { if (k === key) throw new DOMException('Test quota', 'QuotaExceededError'); return original.call(this, k, v); };
      window.restoreMockStorage = () => { Storage.prototype.setItem = original; };
    }, key);
    await page.getByRole('button', { name: 'Lưu draft', exact: true }).click();
    await page.getByText(/Không thể lưu mock vào trình duyệt/).first().waitFor();
    assert.equal(await page.getByLabel('Mô tả sản phẩm', { exact: true }).inputValue(), 'A merchant-edited English product description.');
    await page.evaluate(() => window.restoreMockStorage());
    await page.getByRole('button', { name: 'Lưu draft', exact: true }).click();
    await page.reload(); await page.getByLabel('Mô tả sản phẩm', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Mô tả sản phẩm', { exact: true }).inputValue(), 'A merchant-edited English product description.');
    await page.getByRole('button', { name: 'Gửi review', exact: true }).click();
    await page.getByLabel('Vai trò demo').selectOption('admin');
    assert.equal(await page.getByRole('button', { name: 'Merchant duyệt PKB', exact: true }).count(), 0);
    await page.getByLabel('Vai trò demo').selectOption('merchant');
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Merchant duyệt PKB', exact: true }).click();
    await page.getByRole('button', { name: 'Tạo draft mới', exact: true }).waitFor();
    assert.equal(await page.getByRole('textbox', { name: 'Mô tả sản phẩm', exact: true }).count(), 0);
    await page.reload(); await page.getByRole('button', { name: 'Tạo draft mới', exact: true }).waitFor();
    const v1 = await page.evaluate(key => { const state = JSON.parse(localStorage.getItem(key)); return state.projects.find(p => p.url === 'https://demo.example/tool-a').knowledge[0]; }, key);
    await page.getByRole('button', { name: 'Tạo draft mới', exact: true }).click();
    await page.getByLabel('Mô tả sản phẩm', { exact: true }).fill('A second English revision with additional verified details.');
    await page.getByRole('button', { name: 'Lưu draft', exact: true }).click();
    await page.getByLabel('Phiên bản PKB').selectOption('1');
    assert.equal(await page.getByRole('textbox', { name: 'Mô tả sản phẩm', exact: true }).count(), 0);
    const unchanged = await page.evaluate(key => { const state = JSON.parse(localStorage.getItem(key)); return state.projects.find(p => p.url === 'https://demo.example/tool-a').knowledge[0]; }, key);
    assert.deepEqual(unchanged, v1, 'approved v1 must remain unchanged');
    await page.getByLabel('Phiên bản PKB').selectOption('2');
    await page.evaluate(() => { document.activeElement?.blur(); window.scrollTo(0, 0); });
    await page.screenshot({ path: path.join(output, 'pkb-desktop.png'), fullPage: true });
    await page.getByRole('button', { name: 'Gửi review', exact: true }).click();
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Merchant duyệt PKB', exact: true }).click();
    await page.getByRole('link', { name: 'Mở Content Factory' }).click();
    await page.waitForURL('**/content'); await page.getByRole('button', { name: 'Tạo template', exact: true }).click();
    await page.getByRole('textbox', { name: 'Chỉnh sửa Kịch bản' }).waitFor();
    assert.match(await page.getByRole('textbox', { name: 'Chỉnh sửa Kịch bản' }).inputValue(), /Language: English. PKB version: 2/);
    await page.getByRole('textbox', { name: 'Chỉnh sửa Kịch bản' }).fill('Unsaved sample script');
    page.once('dialog', dialog => dialog.dismiss());
    await page.getByRole('tab', { name: 'Caption', exact: true }).click();
    assert.equal(await page.getByRole('textbox', { name: 'Chỉnh sửa Kịch bản' }).inputValue(), 'Unsaved sample script');
    page.once('dialog', dialog => dialog.accept());
    await page.getByRole('button', { name: 'Tạo lại template', exact: true }).click();
    assert.match(await page.getByRole('textbox', { name: 'Chỉnh sửa Kịch bản' }).inputValue(), /Language: English. PKB version: 2/);
    await page.reload(); await page.getByRole('tab', { name: 'Kịch bản', exact: true }).click();
    assert.match(await page.getByRole('textbox', { name: 'Chỉnh sửa Kịch bản' }).inputValue(), /second English revision/);

    // Canonical duplicate is rejected; different product paths on the same domain remain valid.
    await page.goto(base + '/products');
    await page.getByLabel('Website URL').fill('https://www.demo.example/tool-a/#section');
    await page.getByLabel('Merchant affiliate URL').fill('https://demo.example/?ref=test');
    await page.getByRole('button', { name: 'Thêm sản phẩm', exact: true }).click();
    await page.getByText('Website URL đã có trong workspace. Hãy mở chi tiết sản phẩm hiện có.').waitFor();
    await page.getByLabel('Website URL').fill('https://demo.example/tool-b');
    await page.getByRole('button', { name: 'Thêm sản phẩm', exact: true }).click();
    await page.waitForURL('**/products/*'); assert.notEqual(page.url(), productUrl);
    for (const width of [390, 320]) {
      await page.setViewportSize({ width, height: 844 });
      await page.goto(productUrl); await page.getByRole('button', { name: 'Tạo draft mới' }).waitFor();
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'PKB page must not overflow mobile');
      await page.screenshot({ path: path.join(output, `pkb-mobile-${width}.png`), fullPage: true });
      await page.goto(base + '/products');
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), 'product table must scroll inside its wrapper');
    }
    assert.deepEqual(errors, []);
    console.log('PASS: URL identity, explicit crawl/failure/retry, persistence, unsaved warning, save failure, merchant-only approval, immutable versions, English content and 320/390px layout.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exit(1); });
