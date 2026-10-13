import test from 'node:test';
import assert from 'node:assert/strict';
import { emptyDraft, initialStudio, parseStudio, estimateTokens } from '../src/features/studio/model.ts';

test('existing history migrates into individual projects without losing settings or balances', () => {
  const state = structuredClone(initialStudio);
  const draft = { ...emptyDraft, sourceUrl: 'https://gamma.app', preparedUrl: 'https://gamma.app', prompt: 'Saved prompt', opening: 'Saved opening', ratio: '4:5' };
  delete draft.notes;
  delete draft.projectId;
  delete draft.model;
  delete draft.references;
  state.draft = draft;
  state.requests = [{ ...draft, id: 'saved-history', createdAt: '2026-10-12T03:00:00.000Z', estimatedTokens: 225, status: 'completed' }];
  const restored = parseStudio(JSON.stringify(state));
  assert.equal(restored.requests[0].projectId, 'saved-history');
  assert.equal(restored.requests[0].notes, '');
  assert.equal(restored.requests[0].model, 'veo');
  assert.deepEqual(restored.requests[0].references, []);
  assert.equal(restored.requests[0].prompt, 'Saved prompt');
  assert.equal(restored.requests[0].ratio, '4:5');
  assert.deepEqual(restored.users, state.users);
  assert.deepEqual(restored.plans, state.plans);
});

test('project notes and video settings survive saving while invalid source snapshots are rejected', () => {
  const state = structuredClone(initialStudio);
  state.requests = [{ ...emptyDraft, sourceUrl: 'https://gamma.app', preparedUrl: 'https://gamma.app', prompt: 'Prompt', opening: 'Opening', projectId: 'project-1', notes: 'For students', ratio: '21:9', references: [{ id: 'reference-1', name: 'product.pdf', type: 'application/pdf', size: 1024 }], id: 'generation-1', createdAt: '2026-10-12T03:00:00.000Z', estimatedTokens: 225, status: 'completed' }];
  assert.deepEqual(parseStudio(JSON.stringify(state)).requests, state.requests);
  state.requests[0].preparedUrl = 'https://different.example.com';
  assert.throws(() => parseStudio(JSON.stringify(state)));
});

test('manually entered video counts survive reload and update estimates; invalid quantities are rejected', () => {
  const state = structuredClone(initialStudio);
  state.draft.count = 7;
  assert.equal(parseStudio(JSON.stringify(state)).draft.count, 7);
  assert.equal(estimateTokens(state.draft), estimateTokens(emptyDraft) * 7);
  for (const count of [0, -1, 1.5, Number.MAX_SAFE_INTEGER + 1]) {
    state.draft.count = count;
    assert.throws(() => parseStudio(JSON.stringify(state)));
  }
});
