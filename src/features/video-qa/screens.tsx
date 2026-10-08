"use client";

import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { ArrowLeft, ArrowRight, Download, Flag, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { VideoPlayer } from "../reviews/video-player";
import { useWorkspace } from "../content-factory/workspace-provider";
import { DemoNotice } from "../portals/dashboards";
import { useVideos } from "./provider";
import { checks, decideVideo, flagVideo, videoLabels, type VideoAsset, type VideoStatus } from "./model";

function Status({ asset }: { asset: VideoAsset }) {
  return <span className={`status-chip ${asset.flaggedAt ? "flagged" : asset.status}`}>{asset.flaggedAt ? "Merchant báo sai" : videoLabels[asset.status]}</span>;
}
export function VideoList({ admin = false }: { admin?: boolean }) {
  const { assets, ready, error } = useVideos();
  const [query, setQuery] = useState("");
  const [filter, setFilter] = useState<VideoStatus | "all" | "flagged">(admin ? "pending_review" : "approved");
  const visible = assets.filter(a => `${a.review.title} ${a.review.product}`.toLowerCase().includes(query.toLowerCase()) && (filter === "all" || (filter === "flagged" ? !!a.flaggedAt : filter === "pending_review" && admin ? a.status === "pending_review" || !!a.flaggedAt : a.status === filter)));
  const base = admin ? "/admin/videos" : "/merchant/library";
  return <>
    <div className="page-heading"><div><p className="eyebrow">{admin ? "ADMIN · VIDEO QA" : "MERCHANT · CONTENT LIBRARY"}</p><h1>{admin ? "QA Video" : "Thư viện nội dung"}</h1><p>{admin ? "Kiểm tra video, đối chiếu PKB và duyệt hoặc từ chối với lý do." : "Xem video đã duyệt, tải nội dung mẫu và báo sai cho Admin."}</p></div>{!admin && <Link className="portal-primary" href="/merchant/content">Biên tập nội dung<ArrowRight size={16} /></Link>}</div>
    <DemoNotice />
    <div className="portal-filters"><div className="search-input"><Search size={16} /><Input aria-label="Tìm nội dung" placeholder="Tìm theo sản phẩm hoặc tiêu đề…" value={query} onChange={e => setQuery(e.target.value)} /></div><div><label htmlFor="video-status">Trạng thái</label><select id="video-status" value={filter} onChange={e => setFilter(e.target.value as typeof filter)}><option value="approved">Đã duyệt</option><option value="pending_review">{admin ? "Cần xử lý" : "Chờ duyệt"}</option><option value="rejected">Từ chối</option><option value="archived">Đã lưu trữ</option><option value="flagged">Merchant báo sai</option><option value="all">Tất cả</option></select></div></div>
    {error && <p className="form-error" role="alert">{error}</p>}
    {!ready ? <p role="status">Đang khôi phục thư viện…</p> : <><p className="review-result-count" role="status">{visible.length} video · dữ liệu mẫu</p><section className="asset-grid" aria-label={admin ? "Hàng đợi QA" : "Thư viện video"}>{visible.map(asset => <article className="asset-card" key={asset.review.id}><Link className="asset-cover" href={`${base}/${asset.review.id}`} aria-label={`Xem ${asset.review.title}`}><Image src={asset.review.thumbnailUrl} alt={`Ảnh minh họa ${asset.review.product}`} width={640} height={360} /><span>VIDEO DEMO</span></Link><div className="asset-body"><div className="asset-meta"><span>{asset.review.product}</span><Status asset={asset} /></div><h2><Link href={`${base}/${asset.review.id}`}>{asset.review.title}</Link></h2><p>PKB v{asset.knowledgeVersion} · EN · video minh họa workspace</p>{asset.reason && <p className="asset-reason">{asset.reason}</p>}{asset.flaggedAt && <p className="asset-reason">Báo sai: {asset.flagReason}</p>}<Link className="asset-link" href={`${base}/${asset.review.id}`}>{admin ? "Kiểm tra video" : "Xem nội dung"}<ArrowRight size={14} /></Link></div></article>)}</section>{!visible.length && <div className="empty-list portal-panel"><h2>Không có video phù hợp</h2><p>Thử đổi trạng thái hoặc từ khóa tìm kiếm.</p><Button variant="outline" onClick={() => { setQuery(""); setFilter("all"); }}>Xem tất cả</Button></div>}</>}
  </>;
}
export function VideoDetail({ id, admin = false }: { id: string; admin?: boolean }) {
  const { assets, ready, error } = useVideos();
  const asset = assets.find(a => a.review.id === id);
  const base = admin ? "/admin/videos" : "/merchant/library";
  if (!ready) return <p role="status">Đang tải video…</p>;
  if (!asset) return <section className="empty-list"><h1>Không tìm thấy video</h1><Link href={base}>Về danh sách</Link></section>;
  return <><Link href={base} className="back-link"><ArrowLeft size={14} />{admin ? "Hàng đợi QA" : "Thư viện nội dung"}</Link><div className="page-heading"><div><p className="eyebrow">{admin ? "ADMIN · KIỂM DUYỆT VIDEO" : "MERCHANT · CHI TIẾT NỘI DUNG"}</p><h1>{asset.review.title}</h1><p>{asset.review.product} · PKB v{asset.knowledgeVersion} · English</p></div><Status asset={asset} /></div><DemoNotice />{error && <p role="alert" className="form-error">{error}</p>}<p className="demo-note video-fixture-note">Video là clip workspace không âm thanh; chưa phải footage sản phẩm hoặc bản render 9:16. Checklist dưới đây dùng để thử quy trình QA.</p>{asset.review.videoUrl && <VideoPlayer src={asset.review.videoUrl} title={asset.review.title} poster={asset.review.thumbnailUrl} transcript={asset.review.transcript} />}<VideoActions key={`${id}-${admin}-${asset.updatedAt}`} asset={asset} admin={admin} /></>;
}
function VideoActions({ asset, admin }: { asset: VideoAsset; admin: boolean }) {
  const { updateVideo } = useVideos();
  const { projects } = useWorkspace();
  const project = projects.find(p => p.id === asset.productId);
  const pkb = project?.knowledge.find(v => v.version === asset.knowledgeVersion);
  const [checklist, setChecklist] = useState({ ...asset.checklist });
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState("");
  const actionable = asset.status === "pending_review" || (asset.status === "approved" && !!asset.flaggedAt);
  const previouslyApproved = asset.firstApprovedAt !== null;
  function run(action: () => void, success: string) { try { action(); setFailure(""); setMessage(success); setReason(""); } catch (cause) { setMessage(""); setFailure(cause instanceof Error ? cause.message : "Không thể lưu thay đổi."); } }
  function downloadCaption() {
    const url = URL.createObjectURL(new Blob([`DEMO — not approved for real publishing\n${asset.caption}`], { type: "text/plain;charset=utf-8" }));
    const link = document.createElement("a"); link.href = url; link.download = `${asset.review.id}-caption-demo.txt`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <div className="portal-columns portal-spacing"><section className="portal-panel"><h2>Thông tin nội dung</h2><p className="panel-description">Snapshot PKB dùng để đối chiếu nội dung.</p><dl className="asset-facts"><div><dt>Sản phẩm</dt><dd>{asset.review.product}</dd></div><div><dt>PKB nguồn</dt><dd>v{asset.knowledgeVersion} · {pkb?.status ?? "không tìm thấy"}</dd></div><div><dt>Kiểm duyệt</dt><dd>{videoLabels[asset.status]}</dd></div>{asset.firstApprovedAt && <div><dt>Duyệt lần đầu</dt><dd>{asset.firstApprovedAt} · {asset.reviewedBy}</dd></div>}</dl>{project && <Link className="asset-link" href={admin ? `/admin/pkb/${project.id}` : `/merchant/products/${project.id}`}>Đối chiếu PKB<ArrowRight size={14} /></Link>}<h3 className="portal-spacing">Caption mẫu</h3><p className="caption-preview">{asset.caption}</p>{asset.reason && <p className="report-box">{asset.status === "archived" ? "Lý do lưu trữ" : "Lý do từ chối"}: {asset.reason}</p>}{asset.flaggedAt && <p className="report-box">Merchant báo sai: {asset.flagReason}</p>}{!admin && asset.status === "approved" && <div className="portal-actions"><a className="portal-primary" href={asset.review.videoUrl!} download={`${asset.review.id}-demo.webm`}><Download size={15} />Tải video demo</a><Button variant="outline" onClick={downloadCaption}>Tải caption</Button></div>}{!admin && asset.status !== "approved" && <p className="panel-description">{asset.status === "archived" ? "Video đã lưu trữ, không thể tải để phát hành mới." : "Nội dung chưa được duyệt, chưa thể tải để sử dụng."}</p>}</section>
    <section className="portal-panel"><h2>{admin ? "Quyết định QA" : "Báo sai nội dung"}</h2><p className="panel-description">{admin ? "Kiểm tra từng mục trước khi duyệt. Từ chối cần lý do để Merchant biết phần cần sửa." : "Merchant chỉ báo sai; Admin kiểm tra và lưu trữ video đã duyệt nếu cần thu hồi."}</p>
      {admin ? <><div className="qa-checklist">{checks.map(check => <label key={check.key}><input type="checkbox" checked={checklist[check.key]} disabled={!actionable} onChange={e => setChecklist(current => ({ ...current, [check.key]: e.target.checked }))} />{check.label}</label>)}</div>{actionable ? <>{pkb?.status !== "approved" && <p className="report-box">PKB nguồn chưa được Merchant duyệt. Chưa thể duyệt video này.</p>}<label className="portal-label" htmlFor="qa-reason">{previouslyApproved ? "Lý do lưu trữ" : "Lý do từ chối"}</label><Textarea id="qa-reason" value={reason} onChange={e => setReason(e.target.value)} placeholder="Nêu thông tin sai và phần cần sửa…" /><div className="portal-actions"><Button disabled={pkb?.status !== "approved" || !checks.every(({ key }) => checklist[key])} onClick={() => run(() => updateVideo(asset.review.id, current => decideVideo(current, "approved", checklist, "", pkb?.status === "approved")), "Đã duyệt video demo.")}>{asset.flaggedAt ? "Giữ duyệt, đóng báo sai" : "Duyệt video"}</Button><Button variant="outline" disabled={!reason.trim()} onClick={() => run(() => updateVideo(asset.review.id, current => decideVideo(current, previouslyApproved ? "archived" : "rejected", checklist, reason, pkb?.status === "approved")), previouslyApproved ? "Đã lưu trữ video demo." : "Đã từ chối video demo.")}>{previouslyApproved ? "Lưu trữ video" : "Từ chối video"}</Button></div></> : <p className="panel-description">{asset.status === "archived" ? "Video đã lưu trữ, không thể duyệt lại. Tạo bản video mới nếu cần sửa nội dung." : "Video đã được xử lý. Khi Merchant báo sai, video sẽ quay lại hàng đợi."}</p>}</> : asset.status === "approved" && !asset.flaggedAt ? <><label className="portal-label" htmlFor="flag-reason">Nội dung cần kiểm tra</label><Textarea id="flag-reason" value={reason} onChange={e => setReason(e.target.value)} placeholder="Ví dụ: giá hoặc tính năng trong video không đúng…" /><Button className="portal-spacing" variant="outline" disabled={!reason.trim()} onClick={() => run(() => updateVideo(asset.review.id, current => flagVideo(current, reason)), "Đã gửi báo sai demo tới hàng đợi Admin.")}><Flag size={14} />Gửi báo sai</Button></> : <p className="panel-description">{asset.flaggedAt ? "Báo sai đã gửi; đang chờ Admin xử lý." : "Chỉ có thể báo sai video đã được duyệt."}</p>}
      {failure && <p className="form-error" role="alert">{failure}</p>}{message && <p className="notice" role="status">{message}</p>}
    </section></div>;
}
