"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Search, PanelLeftClose, PanelLeftOpen, LayoutGrid, List } from "lucide-react";
import { usePreferences } from "@/features/studio/preferences";
import { useStudio } from "@/features/studio/provider";
import { emptyDraft } from "@/features/studio/model";
import { projectHistory, requestDraft } from "@/features/studio/projects";
import { Modal } from "@/features/studio/common";
import { useAuth } from "@/features/auth/provider";

export function Header() {
  const pathname = usePathname();
  const router = useRouter();
  const admin = pathname.startsWith("/admin");
  const { account, signOut } = useAuth();
  const { t, number, date, language, theme, setLanguage, setTheme, sidebarCollapsed, setSidebarCollapsed, videoView, setVideoView } = usePreferences();
  const { users, plans, requests, ready, commit, draft } = useStudio();
  const user = users.find(item => item.id === "demo")!;
  const plan = plans.find(item => item.id === user.planId);
  const [settings, setSettings] = useState(false);
  const [sidebar, setSidebar] = useState(false);
  const [mobile, setMobile] = useState(false);
  const [query, setQuery] = useState("");
  const [searchFocused, setSearchFocused] = useState(false);
  const searchRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const media = window.matchMedia("(max-width: 640px)");
    let alive = true;
    queueMicrotask(() => { if (alive) setMobile(media.matches); });
    const resize = () => setMobile(media.matches);
    media.addEventListener("change", resize);
    const outside = (event: PointerEvent) => { if (!searchRef.current?.contains(event.target as Node)) setSearchFocused(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") { setSidebar(false); setSearchFocused(false); } };
    document.addEventListener("pointerdown", outside); document.addEventListener("keydown", escape);
    return () => { alive = false; media.removeEventListener("change", resize); document.removeEventListener("pointerdown", outside); document.removeEventListener("keydown", escape); };
  }, []);
  const navigation = [
    { label: t("Người dùng", "Users"), href: "/admin/users" },
    { label: "Token", href: "/admin/tokens" },
    { label: t("Gói đăng ký", "Plans"), href: "/admin/plans" },
    { label: "PKB", href: "/admin/pkb" },
  ];
  const projects = projectHistory(requests);
  const needle = query.trim().toLocaleLowerCase();
  const matching = projects.filter(project => requests.some(request => (request.projectId ?? request.id) === project.id && `${project.title} ${request.sourceUrl} ${request.notes} ${request.prompt} ${request.references.map(file => file.name).join(" ")}`.toLocaleLowerCase().includes(needle)));
  const current = projects.find(p => pathname === `/creator/project/${p.id}` || (pathname === "/creator/create" && draft.projectId === p.id));
  const pageName = admin ? navigation.find(item => pathname.startsWith(item.href))?.label : current?.title ?? t("Dự án mới", "New project");
  const displayName = account?.name ?? user.name;
  const initials = displayName.split(" ").map(part => part[0]).slice(-2).join("").toUpperCase();
  const expanded = mobile ? sidebar : !sidebarCollapsed;
  function newProject() {
    try { commit(s => ({ ...s, draft: { ...emptyDraft } })); setError(""); setSidebar(false); router.push("/creator/create"); }
    catch { setError(t("Chưa mở được dự án mới. Hãy tải lại trang.", "Could not open a new project. Reload and retry.")); }
  }
  function openProject(id: string) {
    const project = projects.find(p => p.id === id);
    if (!project) return;
    try { commit(s => s.draft.projectId === id ? s : ({ ...s, draft: requestDraft(project.latest) })); setError(""); setSidebar(false); setSearchFocused(false); setQuery(""); router.push(`/creator/project/${id}`); }
    catch { setError(t("Chưa mở được dự án. Hãy tải lại trang.", "Could not open the project. Reload and retry.")); }
  }
  function logout() {
    try { signOut(); }
    catch { setError(t("Chưa đăng xuất được. Hãy thử lại.", "Could not sign out. Please retry.")); }
  }
  return <>
    <a className="studio-skip" href="#main-content">{t("Đến nội dung", "Skip to content")}</a>
    <aside id="workspace-sidebar" className={`studio-sidebar ${!admin ? "project-sidebar" : ""} ${sidebar ? "sidebar-open" : ""}`}>
      <Link className="studio-brand" href={admin ? "/admin/users" : "/creator/create"}>reviewlab<span>.</span></Link>
      {admin ? <nav aria-label={t("Điều hướng", "Navigation")}>{navigation.map(item => <Link key={item.href} href={item.href} className={pathname.startsWith(item.href) ? "active" : ""} aria-current={pathname.startsWith(item.href) ? "page" : undefined} onClick={() => setSidebar(false)}>{item.label}</Link>)}</nav> : <>
        <button className="new-project-button" type="button" disabled={!ready} onClick={newProject}>{t("Tạo dự án mới", "New project")}<span aria-hidden="true">+</span></button>
        <div className="project-list-label">{t("Dự án của bạn", "Your projects")}</div>
        <nav className="project-list" aria-label={t("Dự án", "Projects")}>
          {projects.map(project => <button key={project.id} className={current?.id === project.id ? "active" : ""} type="button" aria-current={current?.id === project.id ? "page" : undefined} disabled={!ready} onClick={() => openProject(project.id)}><strong>{project.title}</strong><small>{date(project.latest.createdAt)} · {project.count} {t("lần tạo", "generations")}</small></button>)}
          {!projects.length && <p className="project-empty">{t("Các dự án sẽ xuất hiện ở đây.", "Your projects will appear here.")}</p>}
        </nav>
      </>}
      {error && <p role="alert" className="studio-error">{error}</p>}
      <div className="sidebar-account"><span className="demo-label">{t("Dữ liệu mẫu", "Sample data")}</span></div>
    </aside>
    <button type="button" className="sidebar-collapse-button" aria-label={expanded ? t("Ẩn menu bên trái", "Hide sidebar") : t("Hiện menu bên trái", "Show sidebar")} title={expanded ? t("Ẩn menu bên trái", "Hide sidebar") : t("Hiện menu bên trái", "Show sidebar")} aria-controls="workspace-sidebar" aria-expanded={expanded} onClick={() => mobile ? setSidebar(!sidebar) : setSidebarCollapsed(!sidebarCollapsed)}>{expanded ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}</button>
    <header className="studio-topbar">
      <div className="topbar-start"><span className="current-page">{pageName}</span></div>
      <div className="navigation-search" ref={searchRef}>
        <Search size={15} aria-hidden="true" />
        <input type="search" aria-label={t("Tìm dự án và video", "Search projects and videos")} placeholder={t("Tìm dự án, video…", "Search projects, videos…")} value={query} onFocus={() => setSearchFocused(true)} onChange={e => { setQuery(e.target.value); setSearchFocused(true); }} onKeyDown={e => { if (e.key === "Enter" && needle && matching[0]) { e.preventDefault(); openProject(matching[0].id); } }} />
        {searchFocused && needle && <div className="navigation-search-results" role="region" aria-label={t("Kết quả tìm kiếm", "Search results")}>{matching.map(project => <button type="button" key={project.id} onClick={() => openProject(project.id)}><strong>{project.title}</strong><small>{project.count} {t("lần tạo", "generations")} · {project.latest.notes || project.latest.sourceUrl}</small></button>)}{!matching.length && <p>{t("Không tìm thấy dự án hoặc video.", "No matching projects or videos.")}</p>}</div>}
      </div>
      <div className="topbar-user">
        {!admin && <span className="header-tokens">{number(user.tokens)} token</span>}
        <button type="button" className="preference-shortcut" aria-label={t("Cài đặt", "Settings")} onClick={() => setSettings(true)}>{language.toUpperCase()} · {theme === "light" ? t("Sáng", "Light") : t("Tối", "Dark")}</button>
        <button type="button" className="account-menu-button" aria-label={t("Cài đặt tài khoản", "Account settings")} onClick={() => setSettings(true)}><span className="avatar">{initials}</span><span className="header-user-name">{displayName}</span></button>
      </div>
    </header>
    {settings && <Modal title={t("Cài đặt", "Settings")} close={() => setSettings(false)}>
      <section className="settings-account" aria-label={t("Tài khoản mẫu", "Demo account")}>
        <div className="settings-account-heading"><strong>{displayName}</strong><span>{t("Tài khoản mẫu", "Demo account")}</span></div>
        <p className="field-hint">{account?.email}</p>
        <div className="settings-account-values">
          <div><span>{t("Token hiện có", "Available tokens")}</span><strong>{number(user.tokens)} <small>token</small></strong></div>
          <div><span>{t("Gói đăng ký", "Subscription plan")}</span><strong>{plan?.name ?? "—"}</strong>{plan && !plan.active && <small>{t("Gói tạm dừng", "Plan paused")}</small>}</div>
        </div>
      </section>
      <div className="settings-row"><div><strong>{t("Ngôn ngữ", "Language")}</strong><p>{t("Ngôn ngữ hiển thị giao diện", "Interface language")}</p></div><div className="segmented"><button type="button" aria-pressed={language === "vi"} onClick={() => setLanguage("vi")}>Tiếng Việt</button><button type="button" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>English</button></div></div>
      <div className="settings-row"><div><strong>{t("Giao diện", "Appearance")}</strong><p>{t("Chọn chế độ hiển thị", "Choose a color theme")}</p></div><div className="segmented"><button type="button" aria-pressed={theme === "light"} onClick={() => setTheme("light")}>{t("Sáng", "Light")}</button><button type="button" aria-pressed={theme === "dark"} onClick={() => setTheme("dark")}>{t("Tối", "Dark")}</button></div></div>
      <div className="settings-row"><div><strong>{t("Kiểu xem video", "Video layout")}</strong><p>{t("Cách sắp xếp video trong dự án", "Arrange videos in your project")}</p></div><div className="segmented"><button type="button" aria-pressed={videoView === "grid"} onClick={() => setVideoView("grid")}><LayoutGrid size={14} />{t("Lưới", "Grid")}</button><button type="button" aria-pressed={videoView === "list"} onClick={() => setVideoView("list")}><List size={14} />{t("Liệt kê", "List")}</button></div></div>
      <div className="settings-footer">{account?.role === "admin" && <Link className="text-button" onClick={() => setSettings(false)} href={admin ? "/creator/create" : "/admin/users"}>{admin ? t("Mở Creator", "Open Creator") : t("Mở Admin", "Open Admin")}</Link>}<button type="button" className="text-button" onClick={logout}>{t("Đăng xuất", "Sign out")}</button></div>
    </Modal>}
  </>;
}
