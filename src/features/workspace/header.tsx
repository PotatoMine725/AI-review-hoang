"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { FileText, Globe, LayoutDashboard, Menu, PlaySquare, X, ShieldCheck, Plus, Library, ArrowLeftRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "@/features/content-factory/workspace-provider";

const legacyNavigation = [
  { label: "Tổng quan", icon: LayoutDashboard, href: "/" },
  { label: "Sản phẩm", icon: Globe, href: "/products" },
  { label: "Nội dung", icon: FileText, href: "/content" },
  { label: "Review video", icon: PlaySquare, href: "/reviews" },
];
const merchantNavigation = [
  { label: "Dashboard", icon: LayoutDashboard, href: "/merchant" },
  { label: "Onboarding", icon: Plus, href: "/merchant/onboarding" },
  { label: "Sản phẩm & PKB", icon: Globe, href: "/merchant/products" },
  { label: "Thư viện nội dung", icon: Library, href: "/merchant/library" },
  { label: "Biên tập nội dung", icon: FileText, href: "/merchant/content" },
];
const adminNavigation = [
  { label: "Tổng quan QA", icon: LayoutDashboard, href: "/admin" },
  { label: "QA Video", icon: ShieldCheck, href: "/admin/videos" },
  { label: "Kiểm tra PKB", icon: Globe, href: "/admin/pkb" },
];

export function Header() {
  const pathname = usePathname();
  const { projects } = useWorkspace();
  const admin = pathname.startsWith("/admin");
  const creator = pathname.startsWith("/creator");
  const legacy = !creator && !admin && pathname !== "/" && !pathname.startsWith("/merchant");
  const navigation = creator ? [{ label: "Thư viện nội dung", icon: Library, href: "/creator/library" }, { label: "Campaigns", icon: Globe, href: "/creator/campaigns" }] : admin ? adminNavigation : legacy ? legacyNavigation : merchantNavigation;
  const home = creator ? "/creator/library" : admin ? "/admin" : "/merchant";
  const area = creator ? "Creator" : admin ? "Admin" : "Merchant";
  const [menuOpen, setMenuOpen] = useState(false);
  const toggle = useRef<HTMLButtonElement>(null);
  const active = [...navigation].reverse().find(({ href }) => href === pathname || (pathname === "/" && href === "/merchant") ||
    (href !== home && pathname.startsWith(href + "/")) ||
    (href === "/products" && pathname.startsWith("/products/")) ||
    (href === "/reviews" && pathname.startsWith("/review/")));

  useEffect(() => {
    if (!menuOpen) return;
    function close(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setMenuOpen(false);
        toggle.current?.focus();
      }
    }
    window.addEventListener("keydown", close);
    return () => window.removeEventListener("keydown", close);
  }, [menuOpen]);

  return (
    <>
      <a className="skip-link" href="#main-content">Đến nội dung chính</a>
      <header className="factory-header workspace-header">
        <Link href={home} className="mobile-brand" onClick={() => setMenuOpen(false)}>reviewlab<span>.</span></Link>
        <div className="breadcrumb">{area} <span>/</span><strong>{active?.label ?? "Dashboard"}</strong></div>
        <span className="area-badge">{area} · Demo</span>
        <Button ref={toggle} className="menu-toggle" variant="outline" size="icon" aria-label={menuOpen ? "Đóng điều hướng" : "Mở điều hướng"} aria-controls="workspace-navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
          {menuOpen ? <X size={20} /> : <Menu size={20} />}
        </Button>
      </header>
      <aside id="workspace-navigation" className={`factory-sidebar workspace-sidebar ${menuOpen ? "menu-open" : ""}`}>
        <Link href={home} className="brand" onClick={() => setMenuOpen(false)}>reviewlab<span className="brand-dot">.</span></Link>
        <p className="nav-label">{creator ? "CREATOR WORKSPACE" : admin ? "KIỂM DUYỆT NỀN TẢNG" : "MERCHANT WORKSPACE"}</p>
        <nav aria-label="Điều hướng chính">
          {navigation.map(({ label, icon: Icon, href }) => (
            <Link key={href} href={href} className={`nav-item ${active?.href === href ? "active" : ""}`} aria-current={active?.href === href ? "page" : undefined} onClick={() => setMenuOpen(false)}>
              <Icon size={19} />{label}{href.endsWith("/products") && <span className="nav-count">{projects.length}</span>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-bottom role-switch"><span>{area} workspace</span><small>Dữ liệu mẫu · chưa đăng nhập</small><Link href={admin ? "/merchant" : "/admin"} onClick={() => setMenuOpen(false)}><ArrowLeftRight size={14} />{admin ? "Chuyển sang Merchant" : "Chuyển sang Admin"}</Link>{!creator && <Link href="/creator/library" onClick={() => setMenuOpen(false)}>Chuyển sang Creator</Link>}{creator && <Link href="/merchant" onClick={() => setMenuOpen(false)}>Chuyển sang Merchant</Link>}</div>
      </aside>
    </>
  );
}
