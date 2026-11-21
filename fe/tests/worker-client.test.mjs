import test from 'node:test';
import assert from 'node:assert/strict';
import { createWorkerClient, WorkerApiError } from '../src/lib/api/worker.ts';

const json = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
function make(handler, token = 'tok') {
  const calls = [];
  const fetch = async (url, init) => { calls.push({ url, init }); return handler(url, init, calls.length); };
  return { calls, client: createWorkerClient({ baseUrl: 'http://w:8000/', getToken: async () => token, fetch }) };
}

test('sends Bearer token and JSON body to the contract path', async () => {
  const { client, calls } = make(() => json(201, { id: 'p1', website_url: 'https://x.com', name: null, status: 'draft' }));
  const product = await client.createProduct({ website_url: 'https://x.com' });
  assert.equal(product.id, 'p1');
  assert.equal(calls[0].url, 'http://w:8000/products');
  assert.equal(calls[0].init.method, 'POST');
  assert.equal(calls[0].init.headers.Authorization, 'Bearer tok');
  assert.equal(calls[0].init.body, '{"website_url":"https://x.com"}');
});

test('maps FastAPI errors to WorkerApiError with detail', async () => {
  const { client } = make(() => json(422, { detail: 'PKB version 1 chưa được duyệt' }));
  await assert.rejects(client.generateScript('p1', { knowledge_version: 1, idempotency_key: 'k' }), e => e instanceof WorkerApiError && e.status === 422 && e.detail.includes('chưa được duyệt'));
  const validation = make(() => json(422, { detail: [{ msg: 'field required' }, { msg: 'bad url' }] }));
  await assert.rejects(validation.client.createProduct({ website_url: '' }), e => e.detail === 'field required; bad url');
});

test('fails fast without token or base URL and reports network failures', async () => {
  await assert.rejects(make(() => json(200, {}), null).client.getJob('j'), e => e.status === 401);
  await assert.rejects(createWorkerClient({ baseUrl: undefined, getToken: async () => 't' }).getJob('j'), e => e.status === 0);
  await assert.rejects(make(() => { throw new TypeError('fetch failed'); }).client.getJob('j'), e => e.status === 0 && /kết nối/.test(e.detail));
});

test('waitForJob polls until a terminal status, tolerates transient 5xx, stops on 4xx', async () => {
  const states = [json(200, { id: 'j', status: 'queued' }), json(502, { detail: 'x' }), json(200, { id: 'j', status: 'running' }), json(200, { id: 'j', status: 'completed' })];
  const seen = [];
  const a = make((_u, _i, n) => states[n - 1]);
  const job = await a.client.waitForJob('j', { intervalMs: 1, onUpdate: j => seen.push(j.status) });
  assert.equal(job.status, 'completed');
  assert.deepEqual(seen, ['queued', 'running', 'completed']);
  await assert.rejects(make(() => json(404, { detail: 'job' })).client.waitForJob('j', { intervalMs: 1 }), e => e.status === 404);
  await assert.rejects(make(() => json(200, { status: 'running' })).client.waitForJob('j', { intervalMs: 5, timeoutMs: 20 }), /sau thời gian chờ/);
});
