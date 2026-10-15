"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { ArrowUpRight } from "lucide-react";
import { Footer } from "@/features/workspace/footer";
import { usePreferences } from "@/features/studio/preferences";
import { LandingFooter, LandingSettings } from "./landing-chrome";
import "./public.css";

export function PublicLayout({ children, landing = false }: { children: ReactNode; landing?: boolean }) {
  const { t } = usePreferences();
  return <>
    <a className="public-skip" href="#main-content">{t("Đến nội dung chính", "Skip to content")}</a>
    <header className={`public-header public-container${landing ? " landing-header" : ""}`}>
      <Link className="public-brand" href="/" aria-label={t("Reviewlab — Trang chủ", "Reviewlab — Home")}>reviewlab<span>.</span></Link>
      <nav className="public-nav" aria-label={t("Điều hướng chính", "Main navigation")}>
        {landing ? <>
          <Link href="/" aria-current="page">Home</Link>
          <Link href="/creator/create">Create</Link>
          <Link href="/#price">Price</Link>
          <Link href="/#about">About</Link>
        </> : <>
          <Link href="/#tinh-nang">{t("Tính năng", "Features")}</Link>
          <Link href="/#quy-trinh">{t("Quy trình", "How it works")}</Link>
        </>}
      </nav>
      <div className="public-account">
        {landing && <LandingSettings />}
        <Link className="public-login" href="/login">{landing ? "Sign in" : t("Đăng nhập", "Sign in")}</Link>
        <Link className="primary-button" href="/signup">{landing ? "Sign up" : t("Đăng ký", "Sign up")}<ArrowUpRight size={15} aria-hidden="true" /></Link>
      </div>
    </header>
    {children}
    {landing ? <LandingFooter /> : <div className="public-container"><Footer /></div>}
  </>;
}
