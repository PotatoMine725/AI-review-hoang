import test from "node:test";
import assert from "node:assert/strict";
import { approvedKnowledge, changeJob, createMockContent, createMockProject, initialWorkspace, latestKnowledge, newDraft, normalizeWebsiteUrl, parseWorkspace, saveKnowledge, transitionKnowledge } from "../src/features/content-factory/model.ts";

function draft() { return changeJob(changeJob(createMockProject("https://demo.example/tool", "https://demo.example/?ref=test", "test"), "running"), "completed"); }
function approve(project) { return transitionKnowledge(transitionKnowledge(project, "in_review", "merchant"), "approved", "merchant"); }
test("canonical URL collapses scheme/www/slash/fragment but retains product paths and query", () => {
  assert.equal(normalizeWebsiteUrl(" HTTP://www.Gamma.app/#hero "), "https://gamma.app");
  assert.notEqual(normalizeWebsiteUrl("https://github.com/features/copilot"), normalizeWebsiteUrl("https://github.com/features/another-product"));
  assert.notEqual(normalizeWebsiteUrl("https://demo.example/tool?a=1"), normalizeWebsiteUrl("https://demo.example/tool?a=2"));
  assert.throws(() => normalizeWebsiteUrl("javascript:alert(1)"));
  assert.throws(() => normalizeWebsiteUrl("https://user:password@demo.example"));
});
test("job state and retry stay explicit; failure doesn't create a PKB", () => {
  const queued = createMockProject("https://demo.example/tool", "https://demo.example", "job");
  assert.equal(queued.job.status, "queued"); assert.equal(queued.knowledge.length, 0);
  assert.throws(() => changeJob(queued, "completed"));
  const failed = changeJob(changeJob(queued, "running"), "failed");
  assert.equal(failed.knowledge.length, 0); assert.ok(failed.job.error);
  const retry = changeJob(failed, "running"); assert.equal(retry.job.id, queued.job.id); assert.equal(retry.job.attempts, 2);
  const completed = changeJob(retry, "completed"); assert.equal(latestKnowledge(completed).status, "draft");
});
test("approved snapshots remain immutable after editing and approving a newer version", () => {
  const v1 = approve(draft()); const snapshot = structuredClone(v1.knowledge[0]);
  assert.throws(() => saveKnowledge(v1, snapshot.data, snapshot.updatedAt));
  let v2 = newDraft(v1, "merchant");
  const edited = structuredClone(latestKnowledge(v2).data);
  edited.facts.description = { value: "A revised English description.", origin: "merchant", sourceId: null, evidence: "" };
  v2 = saveKnowledge(v2, edited, latestKnowledge(v2).updatedAt);
  assert.equal(approvedKnowledge(v2).version, 1);
  v2 = approve(v2);
  assert.equal(approvedKnowledge(v2).version, 2);
  assert.deepEqual(v2.knowledge[0], snapshot);
});
test("merchant-only approval and review state are enforced in the mock domain", () => {
  const p = draft(); assert.throws(() => transitionKnowledge(p, "approved", "merchant"));
  assert.throws(() => transitionKnowledge(p, "in_review", "admin"));
  const review = transitionKnowledge(p, "in_review", "merchant");
  assert.throws(() => transitionKnowledge(review, "approved", "admin"));
  assert.throws(() => transitionKnowledge(review, "rejected", "merchant", "Missing evidence"), /Chỉ admin/);
  assert.throws(() => transitionKnowledge(review, "rejected", "admin"));
  const rejected = transitionKnowledge(review, "rejected", "admin", "Missing evidence");
  assert.equal(latestKnowledge(rejected).status, "rejected"); assert.equal(rejected.currentKnowledgeVersion, null);
  assert.equal(latestKnowledge(newDraft(rejected, "merchant")).version, 2);
});
test("missing required facts or invalid pricing block submission; stale saves fail", () => {
  const p = draft(); const data = structuredClone(latestKnowledge(p).data);
  data.facts.description.value = "";
  const saved = saveKnowledge(p, data, latestKnowledge(p).updatedAt);
  assert.throws(() => transitionKnowledge(saved, "in_review", "merchant"));
  assert.throws(() => saveKnowledge(p, data, "outdated revision"));
  data.facts.description.value = "Example"; data.pricing.plans[0].listPrice = -1;
  assert.throws(() => transitionKnowledge(saveKnowledge(p, data, latestKnowledge(p).updatedAt), "in_review", "merchant"));
});
test("saved workspace round-trips jobs, drafts, approvals and English content snapshots", () => {
  const project = approve(draft()); project.content = createMockContent(project, "Content creators", "YouTube Shorts");
  const saved = { ...structuredClone(initialWorkspace), projects: [newDraft(project, "merchant")], selectedId: project.id };
  const restored = parseWorkspace(JSON.stringify(saved));
  assert.deepEqual(restored, saved);
  assert.equal(restored.projects[0].content.knowledgeVersion, 1);
  assert.match(restored.projects[0].content.script, /Language: English/);
  assert.throws(() => parseWorkspace('{"schema":1}'));
  saved.projects[0].currentKnowledgeVersion = 99; assert.throws(() => parseWorkspace(JSON.stringify(saved)));
});
