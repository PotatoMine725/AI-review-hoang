import { getSupabase } from "../supabase/client";
import { createWorkerClient } from "./worker";

/** Instance dùng trong app: base URL từ env, token lấy từ phiên Supabase hiện tại. */
export const worker = createWorkerClient({
  baseUrl: process.env.NEXT_PUBLIC_WORKER_API_URL,
  getToken: async () => (await getSupabase()?.auth.getSession())?.data.session?.access_token ?? null,
});
