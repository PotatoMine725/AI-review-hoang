import test from 'node:test';
import assert from 'node:assert/strict';
import { summarizePkb, summarizeScript, parseAssets, videoOptions, isActiveJob } from '../src/features/pipeline/model.ts';

test('summarizePkb reads PKB v0.3 fields and tolerates missing ones', () => {
  const summary = summarizePkb({ identity: { name: 'PDFCraft', tagline: 'Công cụ PDF', description: 'd' }, usp: [{ text: 'Chạy trên trình duyệt' }, { nope: 1 }], features: [{ name: 'Gộp PDF' }] });
  assert.deepEqual(summary, { name: 'PDFCraft', tagline: 'Công cụ PDF', description: 'd', usp: ['Chạy trên trình duyệt'], features: ['Gộp PDF'] });
  assert.deepEqual(summarizePkb(null), { name: '', tagline: '', description: '', usp: [], features: [] });
});

test('summarizeScript flattens scene narration', () => {
  const summary = summarizeScript({ estimated_duration_s: 35, concept: { title: 'T' }, hook: { text: 'H' }, cta: { text: 'C' },
    scenes: [{ scene_id: 's01', role: 'hook', narration_segments: [{ segment_id: 's01-u01', text: 'a' }, { segment_id: 's01-u02', text: 'b' }] }] });
  assert.equal(summary.durationS, 35);
  assert.deepEqual(summary.scenes, [{ id: 's01', role: 'hook', narration: 'a b' }]);
  assert.equal(summarizeScript(undefined).scenes.length, 0);
});

test('parseAssets and videoOptions validate worker inputs', () => {
  assert.deepEqual(parseAssets(' '), []);
  assert.deepEqual(parseAssets('[{"asset_id":"a"}]'), [{ asset_id: 'a' }]);
  assert.throws(() => parseAssets('{'), /JSON/);
  assert.throws(() => parseAssets('{"a":1}'), /mảng/);
  assert.deepEqual(videoOptions({ assetsPath: ' D:/a.json ', mode: 'preview', ratios: ['16:9'] }), { assets_path: 'D:/a.json', mode: 'preview', ratios: ['16:9'] });
  assert.throws(() => videoOptions({ assetsPath: '', mode: 'final', ratios: ['16:9'] }), /assets_path/);
  assert.throws(() => videoOptions({ assetsPath: 'x', mode: 'final', ratios: [] }), /tỉ lệ/);
  assert.equal(isActiveJob({ status: 'running' }), true);
  assert.equal(isActiveJob({ status: 'completed' }), false);
});
