"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, type FormEvent } from "react";
import { usePreferences } from "@/features/studio/preferences";
import { useAuth } from "./provider";
import { DEMO_PASSWORD, loginDestination } from "./model";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const signup = mode === "signup";
  const router = useRouter();
  const { t } = usePreferences();
  const { account, ready, error: storageError, signIn, signUp } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (account) router.replace(loginDestination(new URLSearchParams(window.location.search).get("next"), account.role));
  }, [account, router]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending) return;
    setPending(true); setError("");
    try {
      if (signup) await signUp(name, email, password, confirmation);
      else await signIn(email, password);
    } catch (cause) {
      const messages: Record<string, string> = {
        name: t("Tên cần từ 2 đến 80 ký tự.", "Use a name with 2–80 characters."),
        email: t("Nhập email hợp lệ.", "Enter a valid email."),
        password: t("Mật khẩu cần từ 8 đến 128 ký tự.", "Use a password with 8–128 characters."),
        confirmation: t("Mật khẩu xác nhận chưa khớp.", "The passwords do not match."),
        duplicate: t("Email này đã có tài khoản trên trình duyệt. Hãy đăng nhập.", "This email is already registered in this browser. Sign in instead."),
        credentials: t("Email hoặc mật khẩu chưa đúng.", "Incorrect email or password."),
      };
      setError(messages[cause instanceof Error ? cause.message : ""] ?? t("Không lưu được tài khoản mẫu. Kiểm tra bộ nhớ trình duyệt và thử lại.", "Could not save the demo account. Check browser storage and retry."));
    } finally { setPending(false); }
  }

  return <main className="auth-page">
    <aside className="auth-story" aria-label={t("Giới thiệu Reviewlab", "About Reviewlab")}>
      <Link className="auth-story-brand" href="/">reviewlab<span>.</span></Link>
      <div className="auth-story-copy">
        <p className="auth-eyebrow">{t("TỪ Ý TƯỞNG ĐẾN KHUNG HÌNH", "FROM IDEA TO FRAME")}</p>
        <h2>{t("Mỗi sản phẩm,", "Every product,")}<br /><span>{t("một câu chuyện.", "a story to tell.")}</span></h2>
        <p>{t("Một đường link. Không gian riêng để biến thông tin sản phẩm thành video theo cách của bạn.", "One link. Your own space to turn product information into a video with your point of view.")}</p>
      </div>
      <div className="auth-art" aria-hidden="true">
        <div className="auth-art-glow" />
        <div className="auth-art-back" />
        <div className="auth-art-frame">
          <div className="auth-art-topline"><span>REVIEWLAB STUDIO</span><span>09:16</span></div>
          <div className="auth-art-scene"><div className="auth-art-orbit" /><div className="auth-art-object" /><div className="auth-art-object auth-art-object-small" /></div>
          <div className="auth-art-caption"><span>{t("Một góc nhìn mới.", "A fresh perspective.")}</span><div><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /><i /></div></div>
        </div>
        <div className="auth-art-label"><span className="auth-art-dot" />{t("Sáng tạo theo cách của bạn", "Make it your own")}</div>
      </div>
      <div className="auth-story-footer"><span>01 — {t("Thông tin", "Information")}</span><span>02 — {t("Ý tưởng", "Ideas")}</span><span>03 — Video</span></div>
    </aside>
    <section className="auth-card" aria-labelledby="auth-title">
      <Link className="auth-brand" href="/">reviewlab<span>.</span></Link>
      <span className="auth-preview-label">{t("Bản xem thử", "Preview")}</span>
      <div className="auth-heading">
        <p className="auth-eyebrow">{t("KHÔNG GIAN LÀM VIỆC", "YOUR WORKSPACE")}</p>
        <h1 id="auth-title">{signup ? t("Tạo tài khoản", "Create an account") : t("Chào mừng trở lại", "Welcome back")}</h1>
        <p>{signup ? t("Bắt đầu tạo video từ sản phẩm của bạn.", "Start creating videos from your products.") : t("Đăng nhập để tiếp tục các dự án của bạn.", "Sign in to continue your projects.")}</p>
      </div>
      <form className="auth-form" onSubmit={submit}>
        <fieldset disabled={!ready || storageError || pending}>
          {signup && <label>{t("Họ và tên", "Full name")}<input name="name" autoComplete="name" required minLength={2} maxLength={80} value={name} onChange={event => setName(event.target.value)} /></label>}
          <label>Email<input name="email" type="email" autoComplete="email" required maxLength={254} value={email} onChange={event => setEmail(event.target.value)} placeholder="ban@example.com" /></label>
          <label>{t("Mật khẩu", "Password")}<input aria-label={t("Mật khẩu", "Password")} name="password" type="password" autoComplete={signup ? "new-password" : "current-password"} required minLength={signup ? 8 : undefined} maxLength={128} value={password} onChange={event => setPassword(event.target.value)} />{signup && <span className="field-hint">{t("Ít nhất 8 ký tự.", "At least 8 characters.")}</span>}</label>
          {signup && <label>{t("Xác nhận mật khẩu", "Confirm password")}<input name="confirmation" type="password" autoComplete="new-password" required maxLength={128} value={confirmation} onChange={event => setConfirmation(event.target.value)} /></label>}
          {(error || storageError) && <p role="alert" className="studio-error">{error || t("Không đọc được tài khoản mẫu đã lưu. Kiểm tra bộ nhớ trình duyệt.", "Could not read saved demo accounts. Check browser storage.")}</p>}
          <button className="primary-button" type="submit">{pending ? t("Đang xử lý…", "Please wait…") : signup ? t("Tạo tài khoản", "Create account") : t("Đăng nhập", "Sign in")}</button>
        </fieldset>
      </form>
      <p className="auth-switch">{signup ? t("Đã có tài khoản?", "Already have an account?") : t("Chưa có tài khoản?", "New here?")} <Link href={signup ? "/login" : "/signup"}>{signup ? t("Đăng nhập", "Sign in") : t("Đăng ký", "Sign up")}</Link></p>
      {!signup && <details className="auth-demo"><summary>{t("Dùng tài khoản mẫu", "Use a demo account")}</summary><p>Creator: creator@reviewlab.demo<br />Admin: admin@reviewlab.demo<br />{t("Mật khẩu", "Password")}: {DEMO_PASSWORD}</p></details>}
      <p className="auth-notice">{t("Bản xem thử. Tài khoản chỉ lưu trên trình duyệt này; hãy dùng mật khẩu mẫu.", "Preview. Accounts are stored only in this browser; use a demo password.")}</p>
    </section>
  </main>;
}
