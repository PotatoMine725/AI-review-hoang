// Client HTTP duy nhất tới worker FastAPI (hợp đồng: AI-review-BE/docs/specs/api-contract.md).
// Thuần TypeScript, không import module khác để test được bằng node --test.

export type JobStatus = "queued" | "running" | "completed" | "failed";
export type ReviewDecision = "submit" | "approve" | "reject";
export type Product = { id: string; website_url: string; name: string | null; status: string };
export type JobOutput = { ratio: string; ok: boolean; mp4?: string; duration_s?: number };
export type Job = {
  id: string; product_id: string; job_type: "crawl" | "video"; status: JobStatus; error: string | null; attempts: number;
  pkb_version: number | null; script_revision: number | null; render_profile: string | null; n8n_execution_id: string | null;
  result_manifest: { status?: string; outputs?: JobOutput[]; [key: string]: unknown } | null;
  cost_usd: number | null; cost_breakdown: Record<string, unknown>; created_at: string; finished_at: string | null;
};
export type QaFeedback = { message: string; scene_id?: string; segment_id?: string; path?: string };
export type ScriptGenerateRequest = {
  knowledge_version: number; idempotency_key: string; parent_revision?: number;
  permitted_assets?: Record<string, unknown>[]; content_context?: Record<string, unknown>; qa_feedback?: QaFeedback[];
};
export type VideoRequest = {
  pkb_version: number; script_revision: number; idempotency_key: string;
  render_profile?: string; options?: Record<string, unknown>;
};

export type RenderTemplate = { id: string; name: string; description: string };
export type RenderVoice = { id: string; gender: "male" | "female"; region: string; style: string; featured: boolean };
export type RenderCatalog = { templates: RenderTemplate[]; default_template: string; voices: RenderVoice[]; default_voice: string };

export class WorkerApiError extends Error {
  readonly status: number;
  readonly detail: string;
  constructor(status: number, detail: string) { super(detail); this.name = "WorkerApiError"; this.status = status; this.detail = detail; }
}

export type WorkerConfig = {
  baseUrl: string | undefined;
  getToken: () => Promise<string | null>;
  fetch?: typeof fetch;
};
type RequestOptions = { body?: unknown; timeoutMs?: number; signal?: AbortSignal };

// `scripts/generate` chạy đồng bộ qua LLM, có thể mất vài phút.
export const GENERATE_TIMEOUT_MS = 10 * 60_000;

function detailOf(payload: unknown, status: number): string {
  const detail = (payload as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) return detail.map(item => (item as { msg?: string })?.msg).filter(Boolean).join("; ") || `HTTP ${status}`;
  return `HTTP ${status}`;
}

export function createWorkerClient(config: WorkerConfig) {
  const doFetch = config.fetch ?? ((...args: Parameters<typeof fetch>) => fetch(...args));

  async function raw(method: string, path: string, { body, timeoutMs = 15_000, signal }: RequestOptions = {}) {
    if (!config.baseUrl) throw new WorkerApiError(0, "Chưa cấu hình NEXT_PUBLIC_WORKER_API_URL.");
    const token = await config.getToken();
    if (!token) throw new WorkerApiError(401, "Chưa đăng nhập.");
    const timeout = AbortSignal.timeout(timeoutMs);
    try {
      return await doFetch(`${config.baseUrl.replace(/\/$/, "")}${path}`, {
        method, cache: "no-store", signal: signal ? AbortSignal.any([signal, timeout]) : timeout,
        headers: { Authorization: `Bearer ${token}`, Accept: "application/json", ...(body === undefined ? {} : { "Content-Type": "application/json" }) },
        body: body === undefined ? undefined : JSON.stringify(body),
      });
    } catch (cause) {
      if (signal?.aborted) throw cause;
      throw new WorkerApiError(0, timeout.aborted ? "Worker phản hồi quá lâu." : "Không kết nối được worker.");
    }
  }
  async function request<T>(method: string, path: string, options?: RequestOptions): Promise<T> {
    const response = await raw(method, path, options);
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new WorkerApiError(response.status, detailOf(payload, response.status));
    return payload as T;
  }
  const base = (productId: string) => `/products/${encodeURIComponent(productId)}`;

  return {
    createProduct: (body: { website_url: string; name?: string }) => request<Product>("POST", "/products", { body }),
    getProduct: (productId: string) => request<Product>("GET", base(productId)),
    createCrawlJob: (productId: string, idempotencyKey: string) =>
      request<{ job_id: string }>("POST", `${base(productId)}/crawl`, { body: { idempotency_key: idempotencyKey } }),
    getJob: (jobId: string, signal?: AbortSignal) => request<Job>("GET", `/jobs/${encodeURIComponent(jobId)}`, { signal }),
    reviewPkb: (productId: string, version: number, body: { decision: ReviewDecision; note?: string }) =>
      request<{ status: string }>("POST", `${base(productId)}/pkb/${version}/review`, { body }),
    generateScript: (productId: string, body: ScriptGenerateRequest, signal?: AbortSignal) =>
      request<{ revision: number }>("POST", `${base(productId)}/scripts/generate`, { body, timeoutMs: GENERATE_TIMEOUT_MS, signal }),
    reviewScript: (productId: string, revision: number, body: { decision: ReviewDecision; note?: string }) =>
      request<{ status: string }>("POST", `${base(productId)}/scripts/${revision}/review`, { body }),
    getRenderCatalog: (signal?: AbortSignal) => request<RenderCatalog>("GET", "/render/catalog", { signal }),
    createVideoJob: (productId: string, body: VideoRequest) =>
      request<{ job_id: string }>("POST", `${base(productId)}/videos`, { body }),

    /** Thẻ video không gửi được header Authorization nên tải MP4 bằng fetch rồi dùng blob URL (nhớ revokeObjectURL). */
    async videoBlobUrl(jobId: string, ratio: string, signal?: AbortSignal): Promise<string> {
      const response = await raw("GET", `/jobs/${encodeURIComponent(jobId)}/video?ratio=${encodeURIComponent(ratio)}`, { timeoutMs: 120_000, signal });
      if (!response.ok) throw new WorkerApiError(response.status, detailOf(await response.json().catch(() => null), response.status));
      return URL.createObjectURL(await response.blob());
    },

    /** Poll tới khi job `completed` hoặc `failed`. Lỗi mạng thoáng qua không dừng vòng lặp; lỗi 4xx thì dừng. */
    async waitForJob(jobId: string, { intervalMs = 3000, timeoutMs = 30 * 60_000, signal, onUpdate }: { intervalMs?: number; timeoutMs?: number; signal?: AbortSignal; onUpdate?: (job: Job) => void } = {}): Promise<Job> {
      const deadline = Date.now() + timeoutMs;
      for (;;) {
        try {
          const job = await this.getJob(jobId, signal);
          onUpdate?.(job);
          if (job.status === "completed" || job.status === "failed") return job;
        } catch (error) {
          if (!(error instanceof WorkerApiError) || (error.status >= 400 && error.status < 500)) throw error;
        }
        if (Date.now() + intervalMs > deadline) throw new WorkerApiError(0, "Job chưa xong sau thời gian chờ.");
        await new Promise<void>((resolve, reject) => {
          const timer = setTimeout(resolve, intervalMs);
          signal?.addEventListener("abort", () => { clearTimeout(timer); reject(signal.reason); }, { once: true });
        });
      }
    },
  };
}
