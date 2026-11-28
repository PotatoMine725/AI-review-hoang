// Hàm thuần cho trang pipeline thật (không import module khác để test bằng node --test).
type Json = Record<string, unknown>;

const isObject = (value: unknown): value is Json => !!value && typeof value === "object" && !Array.isArray(value);
const text = (value: unknown) => (typeof value === "string" ? value : "");
const objects = (value: unknown): Json[] => (Array.isArray(value) ? value.filter(isObject) : []);

export function summarizePkb(data: unknown) {
  const root = isObject(data) ? data : {};
  const identity = isObject(root.identity) ? root.identity : {};
  return {
    name: text(identity.name) || text(identity.brand_name),
    tagline: text(identity.tagline),
    description: text(identity.description),
    usp: objects(root.usp).map(item => text(item.text)).filter(Boolean),
    features: objects(root.features).map(item => text(item.name)).filter(Boolean),
  };
}

export function summarizeScript(content: unknown) {
  const root = isObject(content) ? content : {};
  const concept = isObject(root.concept) ? root.concept : {};
  const hook = isObject(root.hook) ? root.hook : {};
  const cta = isObject(root.cta) ? root.cta : {};
  return {
    title: text(concept.title),
    hook: text(hook.text),
    cta: text(cta.text),
    durationS: typeof root.estimated_duration_s === "number" ? root.estimated_duration_s : null,
    scenes: objects(root.scenes).map(scene => ({
      id: text(scene.scene_id), role: text(scene.role),
      narration: objects(scene.narration_segments).map(segment => text(segment.text)).filter(Boolean).join(" "),
    })),
  };
}

export const ACTIVE_JOB = ["queued", "running"];
export const isActiveJob = (job: { status: string }) => ACTIVE_JOB.includes(job.status);

export function newKey(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

/** `permitted_assets` tạm do người dùng dán vào cho tới khi BE có bảng assets. Rỗng = không có tư liệu. */
export function parseAssets(raw: string): Json[] {
  if (!raw.trim()) return [];
  let value: unknown;
  try { value = JSON.parse(raw); } catch { throw new Error("permitted_assets không phải JSON hợp lệ."); }
  if (!Array.isArray(value) || value.some(item => !isObject(item))) throw new Error("permitted_assets phải là mảng các object.");
  return value as Json[];
}

export type VideoChoice = { template?: string; voice?: string };

export function videoOptions({ assetsPath, mode, ratios, template, voice }: { assetsPath: string; mode: "preview" | "final"; ratios: string[] } & VideoChoice): Json {
  if (!assetsPath.trim()) throw new Error("Cần assets_path (đường dẫn assets.json trên máy render).");
  if (!ratios.length) throw new Error("Chọn ít nhất một tỉ lệ khung hình.");
  return { assets_path: assetsPath.trim(), mode, ratios, ...(template ? { template } : {}), ...(voice ? { voice } : {}) };
}

/** "Hải Đăng" → "hai-dang": dùng trong render_profile (ASCII, ngắn). */
export function slug(value: string): string {
  return value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/đ/g, "d").replace(/Đ/g, "D").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
}

/** DB chỉ cho 1 video chưa lỗi cho mỗi (revision, render_profile), nên profile gồm chế độ + tỉ lệ + template + giọng để dựng lại bản khác cùng kịch bản. */
export function renderProfile(mode: "preview" | "final", ratios: string[], { template, voice }: VideoChoice = {}): string {
  const parts = [mode, [...ratios].sort().map(ratio => ratio.replace(":", "x")).join("+")];
  if (template || voice) parts.push(template ? slug(template) : "mac-dinh");
  if (voice) parts.push(slug(voice));
  return parts.join("-").slice(0, 100);
}

/** Clip mẫu 3 s (9:16, không tiếng) trong `public/templates/<id>.mp4|.jpg`; template chưa có clip thì chỉ hiện chữ. */
export const TEMPLATE_PREVIEWS = new Set(["nhip-nhanh", "toi-gian", "dem-nguoc", "pixel", "hoat-hinh"]);

export const voiceLabel = (voice: { id: string; gender: string; region: string; style: string }) =>
  `${voice.id} · ${voice.gender === "female" ? "Nữ" : "Nam"} · ${voice.region} · ${voice.style}`;

export const jobLabels: Record<string, string> = { queued: "Đang chờ", running: "Đang chạy", completed: "Hoàn tất", failed: "Lỗi" };
export const reviewLabels: Record<string, string> = { draft: "Bản nháp", in_review: "Chờ duyệt", approved: "Đã duyệt", rejected: "Bị từ chối" };
