// Đọc dữ liệu pipeline trực tiếp từ Supabase dưới RLS (owner chỉ thấy dữ liệu của mình). Ghi đi qua worker.
import { getSupabase } from "../supabase/client";
import type { Job } from "./worker";

export type ProductRow = { id: string; website_url: string; name: string | null; status: string; current_knowledge_version: number | null; created_at: string };
export type ReviewStatus = "draft" | "in_review" | "approved" | "rejected";
export type PkbRow = { product_id: string; version: number; status: ReviewStatus; data: Record<string, unknown>; sources: Record<string, unknown>[]; review_note: string | null; created_at: string };
export type ScriptRow = { product_id: string; revision: number; knowledge_version: number; parent_revision: number | null; status: ReviewStatus; content: Record<string, unknown>; report: Record<string, unknown>; review_note: string | null; created_at: string };

export class DataError extends Error {}

function client() {
  const supabase = getSupabase();
  if (!supabase) throw new DataError("Chưa cấu hình Supabase.");
  return supabase;
}
function unwrap<T>(result: { data: T | null; error: { message: string } | null }): T {
  if (result.error) throw new DataError(result.error.message);
  return result.data as T;
}

export async function listProducts(): Promise<ProductRow[]> {
  return unwrap(await client().from("products").select("id,website_url,name,status,current_knowledge_version,created_at").order("created_at", { ascending: false }));
}
export async function listPkbVersions(productId: string): Promise<PkbRow[]> {
  return unwrap(await client().from("product_knowledge").select("*").eq("product_id", productId).order("version", { ascending: false }));
}
export async function listScripts(productId: string): Promise<ScriptRow[]> {
  return unwrap(await client().from("script_revisions").select("*").eq("product_id", productId).order("revision", { ascending: false }));
}
export async function listJobs(productId: string): Promise<Job[]> {
  return unwrap(await client().from("generation_jobs").select("id,product_id,job_type,status,error,attempts,pkb_version,script_revision,render_profile,n8n_execution_id,result_manifest,cost_usd,cost_breakdown,created_at,finished_at").eq("product_id", productId).order("created_at", { ascending: false }));
}

/** `POST /products` của worker cần hồ sơ merchant của tài khoản. */
export async function ensureMerchant(displayName: string): Promise<string> {
  const supabase = client();
  const existing = unwrap<{ id: string } | null>(await supabase.from("merchants").select("id").maybeSingle());
  if (existing) return existing.id;
  const slug = `${displayName.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").replace(/đ/g, "d").replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 60) || "merchant"}-${crypto.randomUUID().slice(0, 6)}`;
  const created = unwrap<{ id: string }>(await supabase.from("merchants").insert({ company_name: displayName.trim().slice(0, 200) || "Merchant", company_slug: slug }).select("id").single());
  return created.id;
}
