export type Language = "vi" | "en";
export type Theme = "light" | "dark";
export const aspectRatios = ["16:9", "9:16", "1:1", "4:3", "3:4", "3:2", "2:3", "4:5", "5:4", "21:9", "9:21"] as const;
export const videoModels = [{ id: "veo", name: "Veo" }, { id: "kling", name: "Kling" }, { id: "sora", name: "Sora" }] as const;
export type ReferenceFile = { id: string; name: string; type: string; size: number };
export type ProductReview = {
  sourceUrl: string; name: string; description: string; features: string;
  pricing: string; variant: string; sources: string; confirmedAt: string | null;
};
export type Draft = {
  sourceUrl: string; preparedUrl: string; prompt: string; opening: string;
  notes: string; projectId: string | null;
  model: typeof videoModels[number]["id"];
  references: ReferenceFile[];
  productReview: ProductReview | null;
  count: number; ratio: typeof aspectRatios[number]; resolution: "720p" | "1080p";
  style: "cinematic" | "animation" | "realistic" | "minimal";
  duration: number; outputLanguage: Language; camera: "auto" | "static" | "pan";
  negativePrompt: string;
};
export type Request = Draft & { id: string; createdAt: string; estimatedTokens: number; status: "completed" };
export type User = { id: string; name: string; email: string; planId: string; tokens: number; active: boolean };
export type Plan = { id: string; name: string; price: number; tokens: number; active: boolean };
export type Transaction = { id: string; userId: string; amount: number; reason: string; createdAt: string };
export type StudioState = { schema: 1; revision: number; draft: Draft; requests: Request[]; users: User[]; plans: Plan[]; transactions: Transaction[] };
export const STUDIO_KEY = "reviewlab.studio.v1";
export const emptyDraft: Draft = { sourceUrl: "", preparedUrl: "", prompt: "", opening: "", notes: "", projectId: null, model: "veo", references: [], productReview: null, count: 1, ratio: "9:16", resolution: "1080p", style: "cinematic", duration: 15, outputLanguage: "vi", camera: "auto", negativePrompt: "" };
export const initialStudio: StudioState = {
  schema: 1, revision: 0, draft: emptyDraft, requests: [], transactions: [],
  plans: [{ id: "free", name: "Free", price: 0, tokens: 500, active: true }, { id: "creator", name: "Creator", price: 299000, tokens: 5000, active: true }, { id: "pro", name: "Pro", price: 799000, tokens: 15000, active: true }],
  users: [{ id: "demo", name: "Minh Anh", email: "minhanh@example.com", planId: "creator", tokens: 3200, active: true }, { id: "user-2", name: "Hoàng Nam", email: "hoangnam@example.com", planId: "pro", tokens: 12400, active: true }, { id: "user-3", name: "Thu Hà", email: "thuha@example.com", planId: "free", tokens: 350, active: false }],
};
export function normalizeSource(value: string): string {
  const url = new URL(value.trim());
  if (!["https:", "http:"].includes(url.protocol) || !url.hostname.includes(".") || url.username || url.password) throw new Error("url");
  url.hash = "";
  return url.toString().replace(/\/$/, "");
}
export function estimateTokens(draft: Draft): number {
  // UI illustration only; the backend must provide the authoritative quote.
  const modelFactor = { veo: 1, kling: 0.8, sora: 1.2 }[draft.model];
  return Math.ceil(draft.duration * (draft.resolution === "1080p" ? 12 : 8) * (draft.style === "cinematic" ? 1.25 : 1) * modelFactor) * draft.count;
}
export function validDraft(value: Draft): boolean {
  if (value?.preparedUrl) { try { normalizeSource(value.preparedUrl); } catch { return false; } }
  return !!value && ["sourceUrl", "preparedUrl", "prompt", "opening", "negativePrompt", "notes"].every(key => typeof value[key as keyof Draft] === "string") && (value.projectId === null || typeof value.projectId === "string") &&
    Array.isArray(value.references) && value.references.length <= 6 && value.references.every(file => file && typeof file.id === "string" && typeof file.name === "string" && typeof file.type === "string" && Number.isSafeInteger(file.size) && file.size > 0 && file.size <= 10 * 1024 * 1024) &&
    (value.productReview === null || validProductReview(value.productReview)) &&
    videoModels.some(model => model.id === value.model) && Number.isSafeInteger(value.count) && value.count > 0 && aspectRatios.includes(value.ratio) && ["720p", "1080p"].includes(value.resolution) &&
    ["cinematic", "animation", "realistic", "minimal"].includes(value.style) && [5, 10, 15, 30, 60].includes(value.duration) &&
    ["vi", "en"].includes(value.outputLanguage) && ["auto", "static", "pan"].includes(value.camera);
}
function validProductReview(value: ProductReview): boolean {
  if (!value || !["sourceUrl", "name", "description", "features", "pricing", "variant", "sources"].every(key => typeof value[key as keyof ProductReview] === "string")) return false;
  try { normalizeSource(value.sourceUrl); } catch { return false; }
  return value.confirmedAt === null || (typeof value.confirmedAt === "string" && Number.isFinite(Date.parse(value.confirmedAt)));
}
export function productIsConfirmed(draft: Draft): boolean {
  const review = draft.productReview;
  if (!review?.confirmedAt || !Number.isFinite(Date.parse(review.confirmedAt)) || !review.name.trim() || !review.description.trim() || !review.sources.trim()) return false;
  try { return review.sourceUrl === normalizeSource(draft.sourceUrl) && review.sources.split("\n").filter(line => line.trim()).every(line => !!normalizeSource(line)); } catch { return false; }
}
export function parseStudio(raw: string): StudioState {
  const state = JSON.parse(raw) as StudioState;
  // Preserve drafts and history saved before projects and notes were added.
  if (state?.draft) { state.draft.notes ??= ""; state.draft.projectId ??= null; state.draft.model ??= "veo"; state.draft.references ??= []; state.draft.productReview ??= null; }
  if (Array.isArray(state?.requests)) for (const request of state.requests) { if (request) { request.notes ??= ""; request.projectId ??= request.id; request.model ??= "veo"; request.references ??= []; request.productReview ??= null; } }
  if (!state || state.schema !== 1 || !Number.isSafeInteger(state.revision) || state.revision < 0 || !validDraft(state.draft) || !Array.isArray(state.requests) || !Array.isArray(state.users) || !Array.isArray(state.plans) || !Array.isArray(state.transactions)) throw new Error("storage");
  if (!state.plans.length || state.plans.some(p => !p || typeof p.id !== "string" || typeof p.name !== "string" || !p.name.trim() || !Number.isSafeInteger(p.price) || p.price < 0 || !Number.isSafeInteger(p.tokens) || p.tokens < 0 || typeof p.active !== "boolean")) throw new Error("plans");
  if (!state.users.some(u => u.id === "demo") || state.users.some(u => !u || typeof u.id !== "string" || typeof u.name !== "string" || typeof u.email !== "string" || !state.plans.some(p => p.id === u.planId) || !Number.isSafeInteger(u.tokens) || u.tokens < 0 || typeof u.active !== "boolean")) throw new Error("users");
  if (state.requests.some(r => !r || !validDraft(r) || typeof r.id !== "string" || !Number.isFinite(Date.parse(r.createdAt)) || !Number.isSafeInteger(r.estimatedTokens) || r.estimatedTokens < 0 || r.status !== "completed")) throw new Error("requests");
  for (const request of state.requests) if (normalizeSource(request.sourceUrl) !== request.preparedUrl || !request.prompt.trim() || !request.opening.trim()) throw new Error("request source");
  if (state.transactions.some(t => !t || typeof t.id !== "string" || !state.users.some(u => u.id === t.userId) || !Number.isSafeInteger(t.amount) || !t.amount || typeof t.reason !== "string" || !t.reason.trim() || !Number.isFinite(Date.parse(t.createdAt)))) throw new Error("transactions");
  for (const rows of [state.plans, state.users, state.requests, state.transactions]) if (new Set(rows.map(r => r.id)).size !== rows.length) throw new Error("ids");
  return state;
}
