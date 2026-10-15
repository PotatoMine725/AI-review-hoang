"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowUpRight, CodeXml, MessageCircle, Settings } from "lucide-react";
import { Modal } from "@/features/studio/common";
import { usePreferences } from "@/features/studio/preferences";

const repository = "https://github.com/PotatoMine725/AI-review-FE";

export function LandingSettings() {
  const [open, setOpen] = useState(false);
  const { t, language, theme, setLanguage, setTheme } = usePreferences();
  return <>
    <button className="landing-settings-button" type="button" aria-haspopup="dialog" aria-expanded={open} onClick={() => setOpen(true)}><Settings size={15} aria-hidden="true" />Settings</button>
    {open && <Modal title={t("Cài đặt", "Settings")} close={() => setOpen(false)}>
      <div className="settings-row"><div><strong>{t("Ngôn ngữ", "Language")}</strong><p>{t("Ngôn ngữ hiển thị giao diện", "Interface language")}</p></div><div className="segmented" role="group" aria-label={t("Ngôn ngữ", "Language")}><button type="button" aria-pressed={language === "vi"} onClick={() => setLanguage("vi")}>Tiếng Việt</button><button type="button" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>English</button></div></div>
      <div className="settings-row"><div><strong>{t("Giao diện", "Appearance")}</strong><p>{t("Chọn chế độ hiển thị", "Choose a color theme")}</p></div><div className="segmented" role="group" aria-label={t("Giao diện", "Appearance")}><button type="button" aria-pressed={theme === "light"} onClick={() => setTheme("light")}>{t("Sáng", "Light")}</button><button type="button" aria-pressed={theme === "dark"} onClick={() => setTheme("dark")}>{t("Tối", "Dark")}</button></div></div>
    </Modal>}
  </>;
}

export function LandingFooter() {
  const { t } = usePreferences();
  return <footer className="landing-footer">
    <div className="public-container">
      <div className="landing-footer-columns">
        <div className="landing-footer-brand"><Link className="public-brand" href="/" aria-label="Reviewlab — Home">reviewlab<span>.</span></Link><p>{t("Từ thông tin sản phẩm đến câu chuyện video mang góc nhìn của bạn.", "From product information to video stories with your own perspective.")}</p><span className="landing-footer-preview">{t("Không gian sáng tạo · Bản xem thử", "A creative workspace · Preview")}</span></div>
        <nav aria-label={t("Liên kết sản phẩm", "Product links")}><h2>{t("Sản phẩm", "Product")}</h2><Link href="/">Home</Link><Link href="/creator/create">Create</Link><Link href="/#price">Price</Link><Link href="/#about">About</Link></nav>
        <nav aria-label={t("Tài nguyên", "Resources")}><h2>{t("Tài nguyên", "Resources")}</h2><Link href="/#quy-trinh">{t("Quy trình sáng tạo", "How it works")}</Link><a href="https://github.com/PotatoMine725/AI-review-BE/tree/dev/docs" target="_blank" rel="noopener noreferrer">{t("Tài liệu", "Documentation")}<ArrowUpRight size={12} aria-hidden="true" /></a><a href={repository} target="_blank" rel="noopener noreferrer">GitHub<ArrowUpRight size={12} aria-hidden="true" /></a><Link href="/credits">{t("Ghi công / Credits", "Credits")}</Link></nav>
        <div className="landing-footer-contact"><h2>{t("Liên hệ", "Contact us")}</h2><p>{t("Góp ý và trao đổi với nhóm phát triển Reviewlab.", "Share feedback with the Reviewlab team.")}</p><a href={`${repository}/issues`} target="_blank" rel="noopener noreferrer"><MessageCircle size={15} aria-hidden="true" />{t("Gửi góp ý trên GitHub", "Send feedback on GitHub")}</a><a className="landing-footer-github" href={repository} target="_blank" rel="noopener noreferrer" aria-label={t("Reviewlab trên GitHub", "Reviewlab on GitHub")}><CodeXml size={17} aria-hidden="true" /></a></div>
      </div>
      <div className="landing-footer-bottom"><span>© {new Date().getFullYear()} Reviewlab. All rights reserved.</span><span>{t("Sáng tạo từ những điều bạn hiểu.", "Create from what you know.")}</span></div>
    </div>
  </footer>;
}
