"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { useWorkspace } from "./workspace-provider";
import { changeJob, knowledgeErrors, knowledgeFields, latestKnowledge, newDraft, saveKnowledge, transitionKnowledge, type Fact, type KnowledgeData, type KnowledgeField, type KnowledgeVersion, type PricingPlan, type Project } from "./model";
import { confirmDiscard, useUnsavedChanges } from "./use-unsaved-changes";

const statusLabels = { draft: "Bản nháp", in_review: "Đang review", approved: "Đã duyệt", rejected: "Từ chối" };

export function ProductDetail({ id, actor }: { id: string; actor?: "merchant" | "admin" }) {
  const productPath = actor === "admin" ? "/admin/pkb" : actor === "merchant" ? "/merchant/products" : "/products";
  const { projects, ready, storageError } = useWorkspace();
  const project = projects.find(p => p.id === id);
  if (!ready) return <p role="status">Đang khôi phục sản phẩm…</p>;
  if (!project) return <section className="empty-list"><h1>Không tìm thấy sản phẩm</h1><Link href={productPath}>Về danh sách sản phẩm</Link></section>;
  return <><Link href={productPath} className="back-link">← Danh sách sản phẩm</Link><div className="page-heading"><div><p className="eyebrow">{actor === "admin" ? "ADMIN · KIỂM TRA CHÍNH SÁCH" : "MERCHANT · REVIEW PKB"}</p><h1>{project.name}</h1><p>Product: {project.status} · PKB đã duyệt hiện tại: {project.currentKnowledgeVersion ? `v${project.currentKnowledgeVersion}` : "chưa có"}</p></div></div><p className="review-demo-banner">Mock M1 · Vai trò và duyệt chỉ mô phỏng giao diện. PKB tiếng Anh; nguồn/giá là dữ liệu minh họa chưa xác minh.</p>{storageError && <p role="alert" className="form-error">{storageError}</p>}<ProductWorkspace key={id} project={project} actor={actor} /></>;
}
function ProductWorkspace({ project, actor }: { project: Project; actor?: "merchant" | "admin" }) {
  const { updateProject } = useWorkspace();
  const [selectedVersion, setSelectedVersion] = useState<number | null>(null);
  const [error, setError] = useState("");
  const latest = latestKnowledge(project);
  const version = project.knowledge.find(v => v.version === selectedVersion) ?? latest;
  function jobAction(status: Project["job"]["status"]) {
    try { updateProject(project.id, p => changeJob(p, status)); setError(""); setSelectedVersion(null); }
    catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể cập nhật job."); }
  }
  return <>
    <section className="pkb-identity"><div><span>Website URL</span><a href={project.url} target="_blank" rel="noopener noreferrer">{project.url} ↗</a></div><div><span>Merchant affiliate URL</span><a href={project.affiliate} target="_blank" rel="noopener noreferrer">{project.affiliate} ↗</a></div></section>
    <section className="job-panel" aria-label="Job crawl mock"><div className="section-title"><h2>Job crawl</h2><span className={`state-tag ${project.job.status === "completed" ? "ready" : ""}`}>{project.job.status}</span></div><p>{project.job.step}</p><small>Job {project.job.id} · số lần thử: {project.job.attempts}</small>{project.job.error && <p role="alert" className="form-error">{project.job.error}</p>}
      {actor !== "admin" && project.job.status !== "completed" && <details className="mock-job-controls" open><summary>Điều khiển job mock</summary><p>Chọn trạng thái để kiểm tra UI. Không có crawler hoặc thời gian hoàn tất thật.</p><div className="pkb-actions">{["queued", "failed"].includes(project.job.status) && <Button onClick={() => jobAction("running")}>{project.job.status === "failed" ? "Thử lại job mock" : "Bắt đầu job mock"}</Button>}{project.job.status === "running" && <><Button onClick={() => jobAction("completed")}>Hoàn tất job mock</Button><Button variant="outline" onClick={() => jobAction("failed")}>Mô phỏng lỗi crawl</Button></>}</div></details>}
    </section>
    {error && <p role="alert" className="form-error">{error}</p>}
    {version ? <KnowledgeEditor key={`${project.id}-${version.version}`} project={project} version={version} latest={version.version === latest?.version} selectedVersion={version.version} onSelectVersion={setSelectedVersion} onNewVersion={() => setSelectedVersion(null)} actor={actor} /> : <div className="empty-list"><h2>Chưa có PKB</h2><p>Hoàn tất job mock để tạo draft tiếng Anh.</p></div>}
  </>;
}
function KnowledgeEditor({ project, version, latest, selectedVersion, onSelectVersion, onNewVersion, actor }: { project: Project; version: KnowledgeVersion; latest: boolean; selectedVersion: number; onSelectVersion: (version: number) => void; onNewVersion: () => void; actor?: "merchant" | "admin" }) {
  const { role: demoRole, setRole, updateProject, setSelectedId } = useWorkspace();
  const role = actor ?? demoRole;
  const [data, setData] = useState<KnowledgeData>(() => structuredClone(version.data));
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [rejectReason, setRejectReason] = useState("");
  const editable = latest && version.status === "draft" && role === "merchant";
  const dirty = JSON.stringify(data) !== JSON.stringify(version.data);
  useUnsavedChanges(dirty);
  const validation = knowledgeErrors({ ...version, data });
  function action(callback: () => void, message: string) {
    try { callback(); setError(""); setMessage(message); } catch (reason) { setError(reason instanceof Error ? reason.message : "Không thể lưu."); setMessage(""); }
  }
  function updateFact(key: KnowledgeField, value: string) {
    setData(current => ({ ...current, facts: { ...current.facts, [key]: { value, origin: "merchant", sourceId: null, evidence: "" } } }));
  }
  function updatePlan(index: number, patch: Partial<PricingPlan>) {
    setData(current => ({ ...current, pricing: { ...current.pricing, plans: current.pricing.plans.map((p, i) => i === index ? { ...p, ...patch, origin: "merchant", sourceId: null, evidence: "" } : p) } }));
  }
  return <section className="pkb-section">
    <div className="section-heading"><div><h2>Product Knowledge Base</h2><p>v{version.version} · {statusLabels[version.status]} · English{dirty ? " · Có thay đổi chưa lưu" : " · Bản đã lưu"}</p></div><div className="pkb-selectors"><div><label htmlFor="pkb-version">Phiên bản PKB</label><select id="pkb-version" value={selectedVersion} onChange={e => { if (confirmDiscard(dirty)) onSelectVersion(Number(e.target.value)); }}>{[...project.knowledge].reverse().map(v => <option key={v.version} value={v.version}>v{v.version} · {v.status}</option>)}</select></div>{!actor && <div><label htmlFor="demo-role">Vai trò demo</label><select id="demo-role" value={role} onChange={e => { if (!dirty) action(() => setRole(e.target.value as "merchant" | "admin"), "Đã đổi vai trò demo."); else setError("Lưu hoặc bỏ thay đổi trước khi đổi vai trò."); }}><option value="merchant">Merchant</option><option value="admin">Admin (chỉ từ chối PKB)</option></select></div>}</div></div>
    {version.status === "approved" && <p className="pkb-readonly">Bản đã duyệt chỉ đọc · Người duyệt: merchant demo · {version.approvedAt}. Muốn sửa, hãy tạo draft mới.</p>}
    {version.rejectionReason && <p className="form-error">Lý do từ chối: {version.rejectionReason}</p>}
    <div className="pkb-grid">
      {knowledgeFields.map(({ key, label }) => <article className="fact-panel" key={key}><label htmlFor={`pkb-${key}`}>{label}</label>{editable ? <Textarea id={`pkb-${key}`} value={data.facts[key].value} placeholder="Chưa có thông tin" onChange={e => updateFact(key, e.target.value)} /> : <div className="fact-value" id={`pkb-${key}`}>{data.facts[key].value || "Chưa có thông tin"}</div>}<FactSource fact={data.facts[key]} sources={version.sources} approved={version.status === "approved"} /></article>)}
    </div>
    <section className="pricing-panel"><h3>Giá / Gói</h3><p className="demo-note">Giá minh họa để kiểm tra UI, không phải giá thực tế. Không tự quy đổi giá theo chu kỳ.</p><div className="pricing-meta">{(["currency", "region", "locale", "defaultView"] as const).map(key => <div key={key}><label htmlFor={`pricing-${key}`}>{({ currency: "Tiền tệ", region: "Vùng giá", locale: "Locale", defaultView: "Tab giá mặc định" })[key]}</label><Input id={`pricing-${key}`} value={data.pricing[key]} disabled={!editable} onChange={e => setData(current => ({ ...current, pricing: { ...current.pricing, [key]: e.target.value } }))} /></div>)}</div>
      {data.pricing.plans.map((plan, index) => <div className="pricing-plan" key={index}><div className="pricing-meta"><div><label htmlFor={`plan-name-${index}`}>Tên gói</label><Input id={`plan-name-${index}`} value={plan.name} disabled={!editable} onChange={e => updatePlan(index, { name: e.target.value })} /></div><div><label htmlFor={`plan-price-${index}`}>Giá niêm yết</label><Input id={`plan-price-${index}`} type="number" min={0} step="any" value={plan.listPrice} disabled={!editable} onChange={e => updatePlan(index, { listPrice: Number(e.target.value) })} /></div><div><label htmlFor={`plan-promo-${index}`}>Giá khuyến mãi (tùy chọn)</label><Input id={`plan-promo-${index}`} type="number" min={0} step="any" value={plan.promoPrice ?? ""} disabled={!editable} onChange={e => updatePlan(index, { promoPrice: e.target.value ? Number(e.target.value) : null })} /></div><div><label htmlFor={`plan-terms-${index}`}>Điều kiện khuyến mãi</label><Input id={`plan-terms-${index}`} value={plan.promoTerms} disabled={!editable} onChange={e => updatePlan(index, { promoTerms: e.target.value })} /></div><div><label htmlFor={`plan-unit-${index}`}>Đơn vị giá</label><select id={`plan-unit-${index}`} value={plan.priceUnit} disabled={!editable} onChange={e => updatePlan(index, { priceUnit: e.target.value as PricingPlan["priceUnit"] })}><option value="month">month</option><option value="year">year</option><option value="one_time">one_time</option></select></div><div><label htmlFor={`plan-cycle-${index}`}>Chu kỳ thanh toán</label><select id={`plan-cycle-${index}`} value={plan.billingCycle} disabled={!editable} onChange={e => updatePlan(index, { billingCycle: e.target.value as PricingPlan["billingCycle"] })}><option value="monthly">monthly</option><option value="yearly">yearly</option><option value="one_time">one_time</option></select></div></div><label htmlFor={`plan-text-${index}`}>price_text nguyên văn</label><Textarea id={`plan-text-${index}`} value={plan.priceText} disabled={!editable} onChange={e => updatePlan(index, { priceText: e.target.value })} /><FactSource fact={{ value: plan.priceText, origin: plan.origin, sourceId: plan.sourceId, evidence: plan.evidence }} sources={version.sources} /></div>)}
    </section>
    <section className="sources-panel"><h3>Nguồn / Evidence</h3><p className="demo-note">Các URL và excerpt dưới đây là tham chiếu mock, chưa được crawl; không có ảnh bằng chứng thật.</p>{version.sources.map(source => <div key={source.id}><strong>{source.id} · {source.pageType}</strong><a href={source.url} target="_blank" rel="noopener noreferrer">{source.url} ↗</a><small>Ngày crawl / hash: chưa có trong mock</small></div>)}</section>
    {editable && validation.length > 0 && <div className="validation-panel"><strong>Cần bổ sung trước khi gửi duyệt:</strong><ul>{validation.map(text => <li key={text}>{text}</li>)}</ul></div>}
    <div className="pkb-actions">
      {editable && <><Button disabled={!dirty} onClick={() => action(() => updateProject(project.id, p => saveKnowledge(p, data, version.updatedAt)), "Đã lưu draft trong trình duyệt.")}>Lưu draft</Button><Button variant="outline" disabled={!dirty} onClick={() => { if (confirmDiscard(dirty)) { setData(structuredClone(version.data)); setError(""); } }}>Bỏ thay đổi</Button><Button variant="outline" disabled={dirty || validation.length > 0} onClick={() => action(() => updateProject(project.id, p => transitionKnowledge(p, "in_review", role)), "PKB đã chuyển sang in_review.")}>Gửi review</Button></>}
      {latest && version.status === "in_review" && <>{role === "merchant" && <Button onClick={() => { if (window.confirm("Duyệt PKB mẫu này? Bản đã duyệt sẽ chỉ đọc; các suy luận được xác nhận trong phạm vi demo.")) action(() => updateProject(project.id, p => transitionKnowledge(p, "approved", role)), "Đã duyệt PKB mock; giữ snapshot bất biến."); }}>Merchant duyệt PKB</Button>}{role === "admin" && <><div className="reject-input"><label htmlFor="reject-reason">Lý do từ chối</label><Input id="reject-reason" value={rejectReason} onChange={e => setRejectReason(e.target.value)} /></div><Button variant="outline" disabled={!rejectReason.trim()} onClick={() => action(() => updateProject(project.id, p => transitionKnowledge(p, "rejected", role, rejectReason)), "Đã từ chối PKB mock.")}>Từ chối PKB</Button></>}</>}
      {latest && role === "merchant" && ["approved", "rejected"].includes(version.status) && <Button onClick={() => action(() => { updateProject(project.id, p => newDraft(p, role)); onNewVersion(); }, "Đã tạo draft mới. Phiên bản trước được giữ nguyên.")}>Tạo draft mới</Button>}
      {role !== "admin" && <Link href={actor ? "/merchant/content" : "/content"} className="inline-action" onClick={event => { try { setSelectedId(project.id); } catch (cause) { event.preventDefault(); setError(cause instanceof Error ? cause.message : "Không thể chọn sản phẩm."); } }}>Mở Content Factory ↗</Link>}
    </div>
    {error && <p role="alert" className="form-error">{error}</p>}{message && <p role="status" className="notice">{message}</p>}
  </section>;
}
function FactSource({ fact, sources, approved = false }: { fact: Fact; sources: KnowledgeVersion["sources"]; approved?: boolean }) {
  const source = sources.find(s => s.id === fact.sourceId);
  const label = { crawled: "Website (mock)", merchant: "Merchant nhập", inferred: "AI suy luận (mock)" }[fact.origin];
  return <div className="fact-source"><span className={`origin-tag origin-${fact.origin}`}>{label}</span>{fact.origin === "inferred" && <small>{approved ? "Đã được merchant xác nhận trong PKB này (mock)." : "Cần merchant xác nhận trước khi dùng."}</small>}{source && <a href={source.url} target="_blank" rel="noopener noreferrer">{source.id} ↗</a>}{fact.evidence && <details><summary>Evidence mẫu</summary><p>{fact.evidence}</p></details>}</div>;
}
