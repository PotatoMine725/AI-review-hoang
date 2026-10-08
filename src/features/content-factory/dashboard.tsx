"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { ArrowRight, ArrowUpRight, Plus, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useWorkspace } from "./workspace-provider";
import { approvedKnowledge, createMockProject, latestKnowledge, normalizeWebsiteUrl, validAffiliateUrl } from "./model";
import { ContentStudio } from "./content-studio";

export function ContentDashboard({ view = "overview", merchant = false }: { view?: "overview" | "products" | "content" | "onboarding"; merchant?: boolean }) {
  const productPath = merchant ? "/merchant/products" : "/products";
  const contentPath = merchant ? "/merchant/content" : "/content";
  const { projects, ready, storageError, addProject, setSelectedId } = useWorkspace();
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [affiliate, setAffiliate] = useState("");
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState("all");
  const activeNav = { overview: "Tổng quan", products: "Sản phẩm & PKB", content: "Biên tập nội dung", onboarding: "Onboarding sản phẩm" }[view];
  const visible = projects.filter(p => `${p.name} ${p.url}`.toLowerCase().includes(query.toLowerCase()) && (filter === "all" || (filter === "approved" ? !!approvedKnowledge(p) : latestKnowledge(p)?.status !== "approved")));
  function start(event: FormEvent) {
    event.preventDefault(); setError("");
    try {
      const canonical = normalizeWebsiteUrl(url);
      if (!validAffiliateUrl(affiliate)) throw new Error("Nhập Merchant affiliate URL hợp lệ (HTTP/HTTPS).");
      const duplicate = projects.find(p => p.url === canonical);
      if (duplicate) throw new Error("Website URL đã có trong workspace. Hãy mở chi tiết sản phẩm hiện có.");
      const project = createMockProject(canonical, affiliate);
      addProject(project); router.push(`${productPath}/${project.id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể tạo sản phẩm mock."); }
  }
  function openContent(id: string) {
    try { setSelectedId(id); router.push(contentPath); } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể chọn sản phẩm."); }
  }
  return (
    <>
      <div className="page-heading"><div><h1>{activeNav}</h1><p>{view === "content" ? "Tạo template tiếng Anh từ PKB đã được merchant duyệt." : "Nhập sản phẩm, theo dõi job mock và review PKB theo phiên bản."}</p></div>{view === "overview" && <Link className="new-button inline-action" href={merchant ? "/merchant/onboarding" : "/products"}><Plus size={17} />Sản phẩm mới</Link>}</div>
      <p className="review-demo-banner">Mock tuần đầu · Dữ liệu và thao tác duyệt chỉ lưu trong trình duyệt này. Giá/nguồn/nội dung minh họa, chưa crawl hoặc gọi AI thật.</p>
      {!ready && <p role="status">Đang khôi phục workspace…</p>}
      {storageError && <p className="form-error" role="alert">{storageError}</p>}
      {view === "overview" && <section className="overview-grid" aria-label="Tình trạng workspace">
        {[{ label: "Sản phẩm", value: projects.length, text: "Quản lý sản phẩm", href: "/products" }, { label: "Chờ review PKB", value: projects.filter(p => ["draft", "in_review"].includes(latestKnowledge(p)?.status ?? "")).length, text: "Kiểm tra thông tin", href: "/products" }, { label: "Đã có nội dung", value: projects.filter(p => p.content).length, text: "Biên tập nội dung", href: "/content" }].map(item => <Link className="overview-card" href={item.href} key={item.label}><span>{item.label}</span><strong>{item.value}</strong><small>{item.text}<ArrowRight size={14} /></small></Link>)}
      </section>}
      {((view === "products" && !merchant) || view === "onboarding") && <section className="intake-card" id="intake"><div className="intake-form">
        <div className="section-title"><h2>Thêm sản phẩm</h2><span className="soft-tag">English PKB</span></div>
        <p className="section-description">Bắt buộc Website URL và URL affiliate đích của merchant. Sản phẩm khác đường dẫn trên cùng domain vẫn có thể được thêm.</p>
        <form className="onboarding-fields" onSubmit={start} noValidate>
          <div><label htmlFor="product-url">Website URL <span>*</span></label>
          <Input id="product-url" value={url} onChange={e => setUrl(e.target.value)} placeholder="https://gamma.app" disabled={!ready} aria-describedby={error ? "intake-error" : undefined} /></div>
          <div><label htmlFor="affiliate-url">Merchant affiliate URL <span>*</span></label>
          <Input id="affiliate-url" value={affiliate} onChange={e => setAffiliate(e.target.value)} placeholder="https://product.com/?ref=your-id" disabled={!ready} /></div>
          <div className="onboarding-submit"><Button type="submit" disabled={!ready}>Thêm sản phẩm<ArrowRight size={16} /></Button><span>Tạo sản phẩm, sau đó mở trang theo dõi job và review PKB.</span></div>
        </form>
      </div></section>}
      {error && <p className="form-error" role="alert" id="intake-error">{error}</p>}
      {view !== "content" && view !== "onboarding" && <section className="projects-section">
        <div className="section-heading"><div><h2>{view === "overview" ? "Sản phẩm gần đây" : "Sản phẩm của bạn"}</h2><p>Trạng thái product, PKB và job được hiển thị riêng.</p></div>{view === "products" && <div className="list-controls"><div className="search-input"><Search size={15} /><Input aria-label="Tìm sản phẩm" placeholder="Tìm sản phẩm…" value={query} onChange={e => setQuery(e.target.value)} /></div><select aria-label="Lọc trạng thái" value={filter} onChange={e => setFilter(e.target.value)}><option value="all">Tất cả</option><option value="review">Chờ review</option><option value="approved">Có PKB đã duyệt</option></select></div>}</div>
        <div className="project-table-wrap"><table className="project-table"><thead><tr><th>SẢN PHẨM</th><th>PRODUCT</th><th>PKB MỚI NHẤT</th><th>JOB CRAWL</th><th>THAO TÁC</th></tr></thead><tbody>{(view === "overview" ? visible.slice(0, 3) : visible).map(p => <tr key={p.id}><td><div className="product-cell"><span className="product-logo">{p.name.charAt(0)}</span><div><strong>{p.name}</strong><small>{p.url}</small></div></div></td><td>{p.status}</td><td>{latestKnowledge(p) ? `v${latestKnowledge(p)!.version} · ${latestKnowledge(p)!.status}` : "Chưa có PKB"}</td><td>{p.job.status}</td><td><div className="row-actions"><Link href={`${productPath}/${p.id}`} className="inline-action">Review PKB<ArrowUpRight size={14} /></Link><Button variant="ghost" disabled={!ready || !approvedKnowledge(p)} onClick={() => openContent(p.id)}>Content</Button></div></td></tr>)}</tbody></table>{!visible.length && <div className="empty-list"><p>Không tìm thấy sản phẩm phù hợp.</p><Button variant="outline" onClick={() => { setQuery(""); setFilter("all"); }}>Xóa bộ lọc</Button></div>}</div>
      </section>}
      {view === "content" && <ContentStudio productPath={productPath} />}
      <p className="demo-note">PKB, job và content mock đã lưu được khôi phục khi tải lại trang. Nội dung đang sửa cần bấm Lưu draft.</p>
    </>
  );
}
