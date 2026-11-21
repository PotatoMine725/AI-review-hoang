export type Account = { id: string; name: string; email: string; role: "creator" | "admin" };

export function normalizeEmail(email: string) {
  return email.trim().toLowerCase();
}

export function validateRegistration(name: string, email: string, password: string, confirmation: string) {
  if (name.trim().length < 2 || name.trim().length > 80) throw new Error("name");
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizeEmail(email))) throw new Error("email");
  if (password.length < 8 || password.length > 128) throw new Error("password");
  if (password !== confirmation) throw new Error("confirmation");
}

type AuthUser = { id: string; email?: string; user_metadata?: Record<string, unknown>; app_metadata?: Record<string, unknown> };

// Role chỉ lấy từ app_metadata (chỉ service_role ghi được); user_metadata do chính người dùng sửa nên không tin.
// BE hiện chỉ có owner, nên mọi tài khoản thật là creator; admin chỉ để mở các trang admin còn dùng dữ liệu mẫu.
export function accountFromUser(user: AuthUser): Account {
  const email = user.email ?? "";
  const name = typeof user.user_metadata?.name === "string" && user.user_metadata.name.trim() ? user.user_metadata.name.trim() : email.split("@")[0];
  return { id: user.id, name, email, role: user.app_metadata?.role === "admin" ? "admin" : "creator" };
}

export function loginDestination(next: string | null, role: Account["role"]) {
  if (next?.startsWith("/creator/") || (role === "admin" && next?.startsWith("/admin/"))) return next;
  return role === "admin" ? "/admin/users" : "/creator/create";
}
