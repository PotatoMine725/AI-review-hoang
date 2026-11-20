"use client";

import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { usePreferences } from "@/features/studio/preferences";
import { useAuth } from "./provider";
import { loginDestination } from "./model";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const signup = mode === "signup";
  const router = useRouter();
  const { t } = usePreferences();
  const { account, ready, error: storageError, signIn, signUp } = useAuth();
  const [name, setName] = useState("");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [pending, setPending] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (account) router.replace(loginDestination(new URLSearchParams(window.location.search).get("next"), account.role));
  }, [account, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true); setError("");
    try {
      if (signup) await signUp(name, identifier, password, confirmation);
      else await signIn(identifier, password);
    } catch (cause) {
      const messages: Record<string, string> = {
        name: t("Tên cần từ 2 đến 80 ký tự.", "Use a name with 2–80 characters."),
        email: t("Nhập email hợp lệ.", "Enter a valid email."),
        password: t("Mật khẩu cần từ 8 đến 128 ký tự.", "Use a password with 8–128 characters."),
        confirmation: t("Mật khẩu xác nhận chưa khớp.", "The passwords do not match."),
        duplicate: t("Email này đã có tài khoản. Hãy đăng nhập.", "This email is already registered. Sign in instead."),
        credentials: t("Email hoặc mật khẩu chưa đúng.", "Incorrect email or password."),
        confirm: t("Tài khoản đã tạo. Hãy xác nhận email rồi đăng nhập.", "Account created. Confirm your email, then sign in."),
      };
      setError(messages[cause instanceof Error ? cause.message : ""] ?? t("Không kết nối được máy chủ xác thực. Thử lại sau.", "Could not reach the auth server. Retry later."));
    } finally { setPending(false); }
  }

  return <main id="main-content" className={`auth-page${signup ? " auth-signup" : ""}`} tabIndex={-1}>
    <div className="auth-atmosphere" aria-hidden="true"><span className="auth-bubble auth-page-bubble" /><span className="auth-star auth-page-star" /><span className="auth-star auth-page-star-small" /></div>
    <aside className="auth-story" aria-label={t("Giới thiệu Reviewlab", "About Reviewlab")}>
      <Link className="auth-brand" href="/" aria-label={t("Reviewlab — Trang chủ", "Reviewlab — Home")}>reviewlab<span>.</span></Link>
      <div className="auth-story-copy">
        <h2>{signup ? t("Cùng bắt đầu", "Start your") : t("Chào mừng đến với", "Welcome to")}<br /><span>{signup ? t("hành trình sáng tạo.", "creative journey.") : "Reviewlab."}</span></h2>
        <p>{t("Từ một sản phẩm. Đến câu chuyện của riêng bạn.", "From one product. To a story of your own.")}</p>
      </div>
      <div className="auth-art" aria-hidden="true">
        <span className="auth-bubble auth-bubble-one" /><span className="auth-bubble auth-bubble-two" /><span className="auth-bubble auth-bubble-three" />
        <span className="auth-star auth-star-one" /><span className="auth-star auth-star-two" /><span className="auth-star auth-star-three" />
        <Image src="/images/auth-ai-video.png" alt="" fill sizes="(max-width: 800px) 1px, (max-width: 1180px) 45vw, 560px" loading="eager" className="auth-illustration" />
      </div>
    </aside>
    <div className="auth-content">
      <div className="auth-topline">
        <Link className="auth-brand auth-mobile-brand" href="/" aria-label={t("Reviewlab — Trang chủ", "Reviewlab — Home")}>reviewlab<span>.</span></Link>
        <Link className="auth-home" href="/"><ArrowLeft size={15} aria-hidden="true" />{t("Về trang chủ", "Back to home")}</Link>
      </div>
      <section className="auth-card" aria-labelledby="auth-title">
      <div className="auth-heading">
        <h1 id="auth-title">{signup ? t("Tạo tài khoản", "Create an account") : t("Chào mừng trở lại", "Welcome back")}</h1>
        <p>{signup ? t("Bắt đầu tạo video từ sản phẩm của bạn.", "Start creating videos from your products.") : t("Đăng nhập để tiếp tục các dự án của bạn.", "Sign in to continue your projects.")}</p>
      </div>
      <form className="auth-form" onSubmit={submit}>
        <fieldset disabled={!ready || storageError || pending}>
          {signup && <label>{t("Họ và tên", "Full name")}<input name="name" autoComplete="name" required minLength={2} maxLength={80} value={name} onChange={event => setName(event.target.value)} /></label>}
          <label>Email<input name="email" type="email" autoComplete={signup ? "email" : "username"} required maxLength={254} value={identifier} onChange={event => setIdentifier(event.target.value)} placeholder="ban@example.com" /></label>
          <div className="auth-password-field"><label>{t("Mật khẩu", "Password")}<input aria-label={t("Mật khẩu", "Password")} name="password" type={showPassword ? "text" : "password"} autoComplete={signup ? "new-password" : "current-password"} required minLength={signup ? 8 : undefined} maxLength={128} value={password} onChange={event => setPassword(event.target.value)} /></label><button className="auth-password-toggle" type="button" aria-label={t(showPassword ? "Ẩn mật khẩu" : "Hiện mật khẩu", showPassword ? "Hide password" : "Show password")} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}>{showPassword ? <EyeOff size={17} aria-hidden="true" /> : <Eye size={17} aria-hidden="true" />}</button>{signup && <span className="field-hint">{t("Ít nhất 8 ký tự.", "At least 8 characters.")}</span>}</div>
          {signup && <label>{t("Xác nhận mật khẩu", "Confirm password")}<input name="confirmation" type="password" autoComplete="new-password" required maxLength={128} value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>}
          {(error || storageError) && <p role="alert" className="studio-error">{error || t("Chưa cấu hình Supabase (NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY).", "Supabase is not configured (NEXT_PUBLIC_SUPABASE_URL / NEXT_PUBLIC_SUPABASE_ANON_KEY).")}</p>}
          <button className="primary-button" type="submit">{pending ? t("Đang xử lý…", "Please wait…") : signup ? t("Tạo tài khoản", "Create account") : t("Đăng nhập", "Sign in")}</button>
        </fieldset>
      </form>
      <p className="auth-switch">{signup ? t("Đã có tài khoản?", "Already have an account?") : t("Chưa có tài khoản?", "New here?")} <Link href={signup ? "/login" : "/signup"}>{signup ? t("Đăng nhập", "Sign in") : t("Đăng ký", "Sign up")}</Link></p>
      </section>
    </div>
  </main>;
}
