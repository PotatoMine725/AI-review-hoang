import { createClient, type SupabaseClient } from "@supabase/supabase-js";

let client: SupabaseClient | null = null;

/** Trình duyệt giữ phiên Supabase Auth (localStorage). Chỉ dùng anon key, không bao giờ service role. */
export function getSupabase(): SupabaseClient | null {
  // NEXT_PUBLIC_* phải viết nguyên văn để Next thay giá trị lúc build.
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const anonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!url || !anonKey) return null;
  client ??= createClient(url, anonKey);
  return client;
}
