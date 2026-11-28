"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useAuth } from "@/features/auth/provider";
import { worker } from "@/lib/api/worker-client";
import { WorkerApiError, type Job, type RenderCatalog, type ReviewDecision } from "@/lib/api/worker";
import { ensureMerchant, listJobs, listPkbVersions, listProducts, listScripts, type PkbRow, type ProductRow, type ReviewStatus, type ScriptRow } from "@/lib/api/pipeline-data";
import { isActiveJob, jobLabels, newKey, parseAssets, renderProfile, reviewLabels, summarizePkb, summarizeScript, TEMPLATE_PREVIEWS, videoOptions, voiceLabel, type VideoChoice } from "./model";
import "./pipeline.css";

const TECH_KEY = "reviewlab.pipeline.tech.v1";
const CHOICE_KEY = "reviewlab.pipeline.choice.v1";
const RATIOS = ["16:9", "9:16"];

function messageOf(error: unknown) {
  if (error instanceof WorkerApiError) return error.detail;
  return error instanceof Error ? error.message : "Có lỗi xảy ra.";
}

export function Pipeline() {
  const { account } = useAuth();
  const [products, setProducts] = useState<ProductRow[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [url, setUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    try { const rows = await listProducts(); setProducts(rows); setSelected(current => current ?? rows[0]?.id ?? null); setError(""); }
    catch (cause) { setError(messageOf(cause)); setProducts(current => current ?? []); }
  }, []);
  useEffect(() => { void Promise.resolve().then(refresh); }, [refresh]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setBusy(true); setError("");
    try {
      await ensureMerchant(account?.name ?? "Merchant");
      const product = await worker.createProduct({ website_url: url.trim() });
      await worker.createCrawlJob(product.id, newKey("crawl"));
      setUrl(""); setSelected(product.id);
      await refresh();
    } catch (cause) { setError(messageOf(cause)); }
    finally { setBusy(false); }
  }

  const product = products?.find(item => item.id === selected) ?? null;
  return <div className="pl">
    <h1>Pipeline video (dữ liệu thật)</h1>
    <section className="pl-card" aria-label="Tạo sản phẩm">
      <h2>Thêm sản phẩm</h2>
      <form className="pl-row" onSubmit={create}>
        <input type="url" required placeholder="https://trang-san-pham.com" aria-label="URL sản phẩm" value={url} onChange={event => setUrl(event.target.value)} disabled={busy} />
        <button className="primary-button" type="submit" disabled={busy}>{busy ? "Đang tạo…" : "Tạo và crawl"}</button>
      </form>
      {error && <p role="alert" className="studio-error">{error}</p>}
    </section>
    <section className="pl-card" aria-label="Sản phẩm">
      <h2>Sản phẩm của bạn</h2>
      {products === null && <p className="pl-muted">Đang tải…</p>}
      {products?.length === 0 && <p className="pl-muted">Chưa có sản phẩm nào.</p>}
      <div className="pl-list">{products?.map(item => <button key={item.id} type="button" className={item.id === selected ? "active" : ""} onClick={() => setSelected(item.id)}><strong>{item.name || item.website_url}</strong><small>{item.website_url}</small></button>)}</div>
    </section>
    {product && <ProductPanel key={product.id} product={product} onChanged={refresh} />}
  </div>;
}

type Where = "top" | "crawl" | "pkb" | "script" | "video";
type Data = { pkbs: PkbRow[]; scripts: ScriptRow[]; jobs: Job[] };

function ProductPanel({ product, onChanged }: { product: ProductRow; onChanged: () => void }) {
  const [data, setData] = useState<Data>({ pkbs: [], scripts: [], jobs: [] });
  const [busy, setBusy] = useState<string | null>(null);
  const [notice, setNotice] = useState<{ where: Where; message: string } | null>(null);
  const [techOpen, setTechOpen] = useState(false);
  const [tech, setTech] = useState({ assetsPath: "", assets: "" });
  const [mode, setMode] = useState<"preview" | "final">("preview");
  const [ratios, setRatios] = useState<string[]>(RATIOS);
  const [choice, setChoice] = useState<VideoChoice>({});

  const load = useCallback(async () => {
    try {
      const [pkbs, scripts, jobs] = await Promise.all([listPkbVersions(product.id), listScripts(product.id), listJobs(product.id)]);
      setData({ pkbs, scripts, jobs });
    } catch (cause) { setNotice({ where: "top", message: messageOf(cause) }); }
  }, [product.id]);
  useEffect(() => { void Promise.resolve().then(load); }, [load]);
  useEffect(() => {
    try { const raw = localStorage.getItem(TECH_KEY); if (raw) Promise.resolve().then(() => setTech(JSON.parse(raw))); } catch {}
  }, []);
  useEffect(() => {
    try { const raw = localStorage.getItem(CHOICE_KEY); if (raw) Promise.resolve().then(() => setChoice(JSON.parse(raw))); } catch {}
  }, []);
  function saveChoice(next: VideoChoice) { setChoice(next); try { localStorage.setItem(CHOICE_KEY, JSON.stringify(next)); } catch {} }
  function saveTech(next: typeof tech) { setTech(next); try { localStorage.setItem(TECH_KEY, JSON.stringify(next)); } catch {} }

  // Job đang chạy: poll tới khi xong rồi nạp lại dữ liệu (PKB mới sau crawl, MP4 sau video).
  const activeJob = data.jobs.find(isActiveJob)?.id;
  useEffect(() => {
    if (!activeJob) return;
    const controller = new AbortController();
    worker.waitForJob(activeJob, { signal: controller.signal, onUpdate: job => setData(current => ({ ...current, jobs: current.jobs.map(item => item.id === job.id ? job : item) })) })
      .then(() => { void load(); onChanged(); })
      .catch(cause => { if (!controller.signal.aborted) setNotice({ where: "top", message: messageOf(cause) }); });
    return () => controller.abort();
  }, [activeJob, load, onChanged]);

  // Lỗi của một thao tác hiện ngay tại mục đó và không bị xoá khi nạp lại dữ liệu.
  async function run(where: Where, label: string, action: () => Promise<unknown>) {
    if (busy) return;
    setBusy(label); setNotice(null);
    try { await action(); await load(); onChanged(); }
    catch (cause) {
      const conflict = where === "video" && cause instanceof WorkerApiError && cause.status === 409;
      const message = conflict ? "Kịch bản này đã có video với cấu hình (chế độ, tỉ lệ, template, giọng) này. Đổi một trong số đó, hoặc sinh bản kịch bản mới." : messageOf(cause);
      if (where === "video" && /assets_path|permitted_assets/.test(message)) setTechOpen(true);
      setNotice({ where, message });
      await load();
    }
    finally { setBusy(null); }
  }


  const pkb = data.pkbs[0];
  const approvedPkb = data.pkbs.find(item => item.status === "approved");
  const script = data.scripts[0];
  const approvedScript = data.scripts.find(item => item.status === "approved");
  const crawl = data.jobs.find(job => job.job_type === "crawl");
  const videos = data.jobs.filter(job => job.job_type === "video");

  return <>
    <NoticeAt notice={notice} where="top" />
    <section className="pl-card" aria-label="Crawl">
      <h2>1. Crawl</h2>
      {crawl ? <p><JobBadge job={crawl} /> {crawl.error && <span className="studio-error">{crawl.error}</span>}</p> : <p className="pl-muted">Chưa có job crawl.</p>}
      <div className="pl-row"><button className="secondary-button" type="button" disabled={!!busy || (!!crawl && isActiveJob(crawl))} onClick={() => run("crawl", "crawl", () => worker.createCrawlJob(product.id, newKey("crawl")))}>Crawl lại</button></div>
      <NoticeAt notice={notice} where="crawl" />
    </section>

    <section className="pl-card" aria-label="PKB">
      <h2>2. Tri thức sản phẩm (PKB) {pkb && <Status value={pkb.status} />}</h2>
      {!pkb && <p className="pl-muted">Chưa có PKB. Chờ crawl và extract xong.</p>}
      {pkb && <>
        <PkbSummary row={pkb} />
        {pkb.review_note && <p className="pl-muted">Ghi chú: {pkb.review_note}</p>}
        <ReviewBar status={pkb.status} busy={!!busy} onReview={(decision, note) => run("pkb", "pkb", () => worker.reviewPkb(product.id, pkb.version, { decision, note }))} />
      </>}
      <NoticeAt notice={notice} where="pkb" />
    </section>

    <section className="pl-card" aria-label="Script">
      <h2>3. Kịch bản {script && <Status value={script.status} />}</h2>
      {!approvedPkb && <p className="pl-muted">Cần duyệt PKB trước.</p>}
      <div className="pl-row">
        <button className="primary-button" type="button" disabled={!approvedPkb || !!busy} onClick={() => run("script", "script", async () => {
          if (!approvedPkb) return;
          await worker.generateScript(product.id, { knowledge_version: approvedPkb.version, idempotency_key: newKey("script"), parent_revision: script?.revision, permitted_assets: parseAssets(tech.assets).map(asset => ({ ...asset, product_id: product.id })) });
        })}>{busy === "script" ? "Đang sinh (có thể vài phút)…" : script ? "Sinh bản mới" : "Sinh kịch bản"}</button>
      </div>
      {script && <>
        <ScriptSummary row={script} />
        {script.review_note && <p className="pl-muted">Ghi chú: {script.review_note}</p>}
        <ReviewBar status={script.status} busy={!!busy} onReview={(decision, note) => run("script", "script-review", () => worker.reviewScript(product.id, script.revision, { decision, note }))} />
      </>}
      <NoticeAt notice={notice} where="script" />
    </section>

    <section className="pl-card" aria-label="Video">
      <h2>4. Video</h2>
      {!approvedScript && <p className="pl-muted">Cần duyệt kịch bản trước.</p>}
      <details open={techOpen} onToggle={event => setTechOpen(event.currentTarget.open)}>
        <summary>Tùy chọn kỹ thuật (tạm, đến khi BE có mặc định)</summary>
        <div className="pl-card">
          <label className="pl-field">assets_path (đường dẫn assets.json trên máy render)<input type="text" value={tech.assetsPath} onChange={event => saveTech({ ...tech, assetsPath: event.target.value })} placeholder="D:/Code/.../assets.pdfcraft.json" /></label>
          <label className="pl-field">permitted_assets (JSON, dùng khi sinh kịch bản; product_id tự điền)<textarea value={tech.assets} onChange={event => saveTech({ ...tech, assets: event.target.value })} placeholder='[{"asset_id":"pdfcraft-merge","kind":"screen_recording","source_id":null,"allowed_use":["internal_demo"],"rights_basis":"..."}]' /></label>
        </div>
      </details>
      <RenderPicker choice={choice} onChange={saveChoice} disabled={!!busy} />
      <div className="pl-row">
        <label className="pl-field">Chế độ<select value={mode} onChange={event => setMode(event.target.value as "preview" | "final")}><option value="preview">preview</option><option value="final">final</option></select></label>
        {RATIOS.map(ratio => <label key={ratio} className="pl-row"><input type="checkbox" checked={ratios.includes(ratio)} onChange={event => setRatios(event.target.checked ? [...ratios, ratio] : ratios.filter(item => item !== ratio))} />{ratio}</label>)}
        <button className="primary-button" type="button" disabled={!approvedScript || !approvedPkb || !!busy || videos.some(isActiveJob)} onClick={() => run("video", "video", async () => {
          if (!approvedScript || !approvedPkb) return;
          await worker.createVideoJob(product.id, { pkb_version: approvedScript.knowledge_version, script_revision: approvedScript.revision, idempotency_key: newKey("video"), render_profile: renderProfile(mode, ratios, choice), options: videoOptions({ assetsPath: tech.assetsPath, mode, ratios, ...choice }) });
        })}>Dựng video</button>
      </div>
      <NoticeAt notice={notice} where="video" />
      {videos.map(job => <VideoJob key={job.id} job={job} />)}
    </section>
  </>;
}

/** Chọn template (thẻ có clip mẫu lặp 3 s) và giọng VieNeu cho job video. Bỏ trống = mặc định của máy render. */
function RenderPicker({ choice, onChange, disabled }: { choice: VideoChoice; onChange: (next: VideoChoice) => void; disabled: boolean }) {
  const [catalog, setCatalog] = useState<RenderCatalog | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    worker.getRenderCatalog(controller.signal).then(setCatalog).catch(cause => { if (!controller.signal.aborted) setError(messageOf(cause)); });
    return () => controller.abort();
  }, []);
  if (error) return <p className="pl-muted">Không tải được danh sách template/giọng ({error}). Video dùng mặc định của máy render.</p>;
  if (!catalog) return <p className="pl-muted">Đang tải template và giọng…</p>;

  const template = choice.template && catalog.templates.some(item => item.id === choice.template) ? choice.template : catalog.default_template;
  const voice = choice.voice && catalog.voices.some(item => item.id === choice.voice) ? choice.voice : catalog.default_voice;
  const featured = catalog.voices.filter(item => item.featured);
  const others = catalog.voices.filter(item => !item.featured);
  return <div className="pl-picker">
    {catalog.templates.length === 0
      ? <p className="pl-muted">Máy chạy API không thấy templates.json (PRODUCE_RENDER_V2), video dùng template mặc định.</p>
      : <div role="radiogroup" aria-label="Template video" className="pl-templates">
        {catalog.templates.map(item => <button key={item.id} type="button" role="radio" aria-checked={item.id === template} disabled={disabled}
          className={`pl-template${item.id === template ? " active" : ""}`} onClick={() => onChange({ ...choice, template: item.id })}>
          {TEMPLATE_PREVIEWS.has(item.id)
            ? <video src={`/templates/${item.id}.mp4`} poster={`/templates/${item.id}.jpg`} autoPlay muted loop playsInline preload="metadata" aria-hidden="true" />
            : <span className="pl-template-empty" aria-hidden="true">Chưa có mẫu</span>}
          <strong>{item.name}{item.id === catalog.default_template && <small> · mặc định</small>}</strong>
          <small>{item.description}</small>
        </button>)}
      </div>}
    <label className="pl-field">Giọng đọc (VieNeu)
      <select value={voice} disabled={disabled} onChange={event => onChange({ ...choice, voice: event.target.value })}>
        <optgroup label="Gợi ý">{featured.map(item => <option key={item.id} value={item.id}>{voiceLabel(item)}{item.id === catalog.default_voice ? " (mặc định)" : ""}</option>)}</optgroup>
        <optgroup label="Giọng khác">{others.map(item => <option key={item.id} value={item.id}>{voiceLabel(item)}{item.id === catalog.default_voice ? " (mặc định)" : ""}</option>)}</optgroup>
      </select>
    </label>
  </div>;
}

function NoticeAt({ notice, where }: { notice: { where: Where; message: string } | null; where: Where }) {
  return notice?.where === where ? <p role="alert" className="studio-error">{notice.message}</p> : null;
}

function JobBadge({ job }: { job: Job }) {
  return <span className={`pl-badge ${job.status === "completed" ? "ok" : job.status === "failed" ? "bad" : ""}`}>{jobLabels[job.status] ?? job.status}</span>;
}
function Status({ value }: { value: ReviewStatus }) {
  return <span className={`pl-badge ${value === "approved" ? "ok" : value === "rejected" ? "bad" : ""}`}>{reviewLabels[value]}</span>;
}

function PkbSummary({ row }: { row: PkbRow }) {
  const s = summarizePkb(row.data);
  return <div>
    <p><strong>v{row.version}</strong> · {s.name || "(chưa có tên)"} {s.tagline && <span className="pl-muted">— {s.tagline}</span>}</p>
    {s.description && <p>{s.description}</p>}
    {s.usp.length > 0 && <p className="pl-muted">USP: {s.usp.join(" · ")}</p>}
    {s.features.length > 0 && <p className="pl-muted">Tính năng: {s.features.join(", ")}</p>}
    <details><summary>Xem dữ liệu đầy đủ</summary><pre>{JSON.stringify(row.data, null, 2)}</pre></details>
  </div>;
}

function ScriptSummary({ row }: { row: ScriptRow }) {
  const s = summarizeScript(row.content);
  return <div>
    <p><strong>rev {row.revision}</strong> (PKB v{row.knowledge_version}){s.durationS !== null && <span className="pl-muted"> · ~{s.durationS}s</span>} · {s.title}</p>
    <p>Hook: {s.hook}</p>
    <ul className="pl-scenes">{s.scenes.map(scene => <li key={scene.id}><b>{scene.role}</b>{scene.narration}</li>)}</ul>
    <p>CTA: {s.cta}</p>
  </div>;
}

function ReviewBar({ status, busy, onReview }: { status: ReviewStatus; busy: boolean; onReview: (decision: ReviewDecision, note?: string) => void }) {
  const [note, setNote] = useState("");
  if (status === "approved" || status === "rejected") return null;
  if (status === "draft") return <div className="pl-row"><button className="secondary-button" type="button" disabled={busy} onClick={() => onReview("submit")}>Gửi duyệt</button></div>;
  return <div className="pl-row">
    <button className="primary-button" type="button" disabled={busy} onClick={() => onReview("approve")}>Duyệt</button>
    <input type="text" aria-label="Lý do từ chối" placeholder="Lý do (bắt buộc khi từ chối)" value={note} onChange={event => setNote(event.target.value)} />
    <button className="secondary-button" type="button" disabled={busy || !note.trim()} onClick={() => onReview("reject", note.trim())}>Từ chối</button>
  </div>;
}

function VideoJob({ job }: { job: Job }) {
  const outputs = (job.result_manifest?.outputs ?? []).filter(output => output.ok);
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const created = useRef<string[]>([]);
  useEffect(() => () => { created.current.forEach(url => URL.revokeObjectURL(url)); }, []);
  async function play(ratio: string) {
    setError("");
    try { const url = await worker.videoBlobUrl(job.id, ratio); created.current.push(url); setUrls(current => ({ ...current, [ratio]: url })); }
    catch (cause) { setError(messageOf(cause)); }
  }
  return <div className="pl-card">
    <p><JobBadge job={job} /> <span className="pl-muted">script rev {job.script_revision} · {new Date(job.created_at).toLocaleString("vi-VN")}</span> {job.result_manifest?.status && <span className="pl-muted">· {String(job.result_manifest.status)}</span>}</p>
    {job.error && <p className="studio-error">{job.error}</p>}
    {error && <p role="alert" className="studio-error">{error}</p>}
    <div className="pl-row">{outputs.map(output => urls[output.ratio]
      ? <video key={output.ratio} src={urls[output.ratio]} controls aria-label={`Video ${output.ratio}`} />
      : <button key={output.ratio} className="secondary-button" type="button" onClick={() => play(output.ratio)}>Xem {output.ratio}{output.duration_s ? ` (${Math.round(output.duration_s)}s)` : ""}</button>)}</div>
  </div>;
}
