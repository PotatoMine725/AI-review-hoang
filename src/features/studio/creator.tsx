"use client";

import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type ChangeEvent } from "react";
import { Plus, Play, Mic } from "lucide-react";
import { useWorkspace } from "@/features/content-factory/workspace-provider";
import { latestKnowledge } from "@/features/content-factory/model";
import { useStudio } from "./provider";
import { usePreferences } from "./preferences";
import { Modal } from "./common";
import { aspectRatios, videoModels, estimateTokens, normalizeSource, productIsConfirmed, type Draft, type Request, type ProductReview } from "./model";
import { requestDraft } from "./projects";
import { referenceAccept, saveReferences } from "./references";
import { ReferenceFiles } from "./reference-files";
import { ProjectDetails } from "./project-details";
import { useProductProcessing } from "./product-progress";
import { useAuth } from "@/features/auth/provider";

export function CreatorStudio({ projectId }: { projectId?: string }) {
  const { draft, users, requests, ready, commit } = useStudio();
  const { projects } = useWorkspace();
  const { account } = useAuth();
  const processing = useProductProcessing();
  const { t, number, videoView, language } = usePreferences();
  const router = useRouter();
  const formRef = useRef<HTMLFormElement>(null);
  const uploadRef = useRef<HTMLInputElement>(null);
  const conversationRef = useRef<HTMLDivElement>(null);
  const loadedProject = useRef<string | null>(null);
  const [custom, setCustom] = useState(false);
  const [detailError, setDetailError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceLanguage, setVoiceLanguage] = useState("vi");
  const [voiceText, setVoiceText] = useState("");
  const [error, setError] = useState("");
  const [countInput, setCountInput] = useState<string | null>(null);
  const user = users.find(u => u.id === "demo")!;
  const validSource = (() => { try { normalizeSource(draft.sourceUrl); return true; } catch { return false; } })();
  const prepared = !!draft.preparedUrl && draft.preparedUrl === draft.sourceUrl;
  const estimate = estimateTokens(draft);
  const enteredCount = Number(countInput ?? draft.count);
  const validCountInput = Number.isSafeInteger(enteredCount) && enteredCount > 0 && Number.isSafeInteger(estimateTokens({ ...draft, count: enteredCount }));
  const activeProjectId = projectId ?? draft.projectId;
  const generations = activeProjectId ? requests.filter(r => (r.projectId ?? r.id) === activeProjectId).slice().reverse() : [];

  useEffect(() => {
    if (!projectId) { loadedProject.current = null; return; }
    if (!ready || loadedProject.current === projectId) return;
    const request = requests.find(r => (r.projectId ?? r.id) === projectId);
    if (request) { loadedProject.current = projectId; if (draft.projectId !== projectId) { try { commit(s => ({ ...s, draft: requestDraft(request) })); } catch { loadedProject.current = null; } } }
  }, [projectId, ready, draft.projectId, requests, commit]);
  useEffect(() => {
    const container = conversationRef.current;
    if (!container) return;
    const latest = container.querySelector(".conversation-turn:last-of-type .assistant-result");
    const top = latest ? latest.getBoundingClientRect().top - container.getBoundingClientRect().top + container.scrollTop - 16 : 0;
    container.scrollTo({ top, behavior: "instant" });
  }, [activeProjectId, generations.length, prepared]);

  function update(patch: Partial<Draft>) {
    if (patch.sourceUrl !== undefined) processing.cancel();
    try { commit(s => ({ ...s, draft: { ...s.draft, ...patch } })); setError(""); }
    catch { setError(t("Chưa lưu được thay đổi. Hãy tải lại và thử lại.", "Could not save changes. Reload and retry.")); }
  }
  function prepareProduct() {
    try {
      const url = normalizeSource(draft.sourceUrl);
      if (draft.productReview?.sourceUrl === url) return true;
      const product = projects.find(item => normalizeSource(item.url) === url);
      const knowledge = product ? latestKnowledge(product) : null;
      const review: ProductReview = {
        sourceUrl: url, name: product?.name ?? new URL(url).hostname,
        description: knowledge?.data.facts.description.value ?? t("Mô tả mẫu của sản phẩm. Hãy sửa thông tin trước khi xác nhận.", "Sample product description. Edit the information before confirming."),
        features: knowledge?.data.facts.features.value ?? "", pricing: knowledge?.data.pricing.plans.map(plan => plan.priceText).join("\n") ?? "", variant: "",
        sources: knowledge?.sources.map(source => source.url).join("\n") || url, confirmedAt: null,
      };
      commit(state => ({ ...state, draft: { ...state.draft, productReview: review, preparedUrl: "" } }));
      setDetailError("");
      return true;
    } catch { setDetailError(t("Chưa chuẩn bị được thông tin. Kiểm tra link và bộ nhớ trình duyệt, rồi thử lại.", "Could not prepare product information. Check the link and browser storage, then retry.")); return false; }
  }
  function openDetails() {
    if (!validSource) return;
    setDetailError(""); setCustom(true);
    if (!draft.productReview) void processing.start(prepareProduct);
  }
  function closeDetails() { processing.cancel(); setCustom(false); }
  function changeProduct(patch: Partial<ProductReview>) {
    if (!draft.productReview) return;
    update({ productReview: { ...draft.productReview, ...patch, confirmedAt: null }, preparedUrl: "" });
    setDetailError("");
  }
  function confirmProduct() {
    if (!draft.productReview) return false;
    const review = { ...draft.productReview, confirmedAt: new Date().toISOString() };
    if (!productIsConfirmed({ ...draft, productReview: review })) { setDetailError(t("Kiểm tra tên, mô tả và các link nguồn trước khi xác nhận.", "Check the name, description, and source links before confirming.")); return false; }
    try { commit(state => ({ ...state, draft: { ...state.draft, productReview: review, preparedUrl: "" } })); setDetailError(""); setError(""); return true; }
    catch { setDetailError(t("Chưa lưu được xác nhận. Hãy thử lại.", "Could not save confirmation. Please retry.")); return false; }
  }
  function removeReference(id: string) {
    update({ references: draft.references.filter(file => file.id !== id), productReview: draft.productReview ? { ...draft.productReview, confirmedAt: null } : null, preparedUrl: "" });
  }
  function openVoice() {
    setVoiceLanguage(language);
    setVoiceText("");
    setVoiceOpen(true);
  }
  function useVoiceNotes() {
    const text = voiceText.trim();
    if (!text) return;
    update({ notes: [draft.notes.trim(), text].filter(Boolean).join("\n"), preparedUrl: "" });
    setVoiceOpen(false);
  }
  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []); event.target.value = "";
    if (!files.length) return;
    setUploading(true); setError("");
    try {
      const saved = await saveReferences(files, draft.references.length, account?.id);
      commit(s => s.draft !== draft ? s : ({ ...s, draft: { ...s.draft, references: [...s.draft.references, ...saved], productReview: s.draft.productReview ? { ...s.draft.productReview, confirmedAt: null } : null, preparedUrl: "" } }));
    } catch (error) {
      const code = error instanceof Error ? error.message : "storage";
      setError(code === "count" ? t("Tối đa 6 tệp tham khảo.", "Attach up to 6 reference files.") : code === "type" ? t("Chọn ảnh PNG/JPG/WebP/GIF hoặc PDF/Word/TXT/MD.", "Choose PNG/JPG/WebP/GIF images or PDF/Word/TXT/MD documents.") : code === "size" ? t("Tệp phải lớn hơn 0 và tối đa 10 MB.", "Files must be non-empty and at most 10 MB.") : t("Chưa lưu được tệp tham khảo. Hãy thử lại.", "Could not save reference files. Please retry."));
    } finally { setUploading(false); }
  }
  function prepareDraft(): Draft {
    const url = normalizeSource(draft.sourceUrl);
    const review = draft.productReview?.sourceUrl === url ? draft.productReview : null;
    const name = review?.name || new URL(url).hostname;
    const facts = review ? `${review.description}\n${review.features}\n${review.pricing}\n${review.variant}\n${t("Nguồn", "Sources")}:\n${review.sources}` : null;
    const notes = draft.notes.trim();
    const prompt = draft.outputLanguage === "vi"
      ? `Giới thiệu ${name} từ ${url}. Mở đầu bằng một tình huống sử dụng cụ thể, minh họa tính năng và kết thúc bằng lời mời tìm hiểu thêm.${facts ? `\n\nThông tin sản phẩm mẫu:\n${facts}` : "\n\nDùng nội dung mẫu để xem thử bố cục."}${notes ? `\n\nGhi chú: ${notes}` : ""}\n\nKhông thêm số liệu, giá hoặc cam kết chưa có nguồn.`
      : `Introduce ${name} using ${url}. Open with a practical use case, demonstrate the features and close with an invitation to learn more.${facts ? `\n\nSample product information:\n${facts}` : "\n\nUse sample content to preview the layout."}${notes ? `\n\nNotes: ${notes}` : ""}\n\nDo not invent statistics, prices or unsupported claims.`;
    const opening = draft.outputLanguage === "vi" ? `${name} ở trung tâm. Nền đơn giản, ánh sáng mềm, tiêu đề ngắn giới thiệu sản phẩm.` : `${name} centered in the frame. Simple background, soft lighting and a short product title.`;
    const references = draft.references.length ? `\n\n${t("Tệp tham khảo đã chọn", "Selected reference files")}: ${draft.references.map(file => file.name).join(", ")}` : "";
    return { ...draft, sourceUrl: url, preparedUrl: url, prompt: prompt + references, opening };
  }
  function previewPrompt() {
    try { const next = prepareDraft(); commit(s => ({ ...s, draft: next })); setError(""); }
    catch { setError(t("Nhập link HTTP/HTTPS hợp lệ, ví dụ https://gamma.app.", "Enter a valid HTTP/HTTPS link, such as https://gamma.app.")); }
  }
  function generate(event: FormEvent) {
    event.preventDefault();
    if (!validSource) { setError(t("Nhập link HTTP/HTTPS hợp lệ trước khi tạo video mẫu.", "Enter a valid HTTP/HTTPS link before creating a sample video.")); return; }
    if (!productIsConfirmed(draft)) { openDetails(); setDetailError(t("Kiểm tra và xác nhận thông tin sản phẩm trước khi tạo video mẫu.", "Review and confirm product information before creating a sample video.")); return; }
    let next: Draft;
    try { next = prepared ? draft : prepareDraft(); }
    catch { setError(t("Nhập link HTTP/HTTPS hợp lệ, ví dụ https://gamma.app.", "Enter a valid HTTP/HTTPS link, such as https://gamma.app.")); return; }
    if (!next.prompt.trim() || !next.opening.trim()) { setError(t("Điền prompt và khung mở đầu trong Chi tiết dự án.", "Fill in the prompt and opening frame in Project details.")); return; }
    if (!user.active || estimate > user.tokens) { setError(t("Tài khoản tạm dừng hoặc không đủ token mẫu.", "The demo account is paused or has insufficient sample tokens.")); return; }
    const id = next.projectId ?? crypto.randomUUID();
    try {
      commit(s => {
        const currentUser = s.users.find(u => u.id === "demo")!;
        if (!currentUser.active || currentUser.tokens < estimate) throw new Error("balance");
        const now = new Date().toISOString();
        const request: Request = { ...next, projectId: id, id: crypto.randomUUID(), status: "completed", createdAt: now, estimatedTokens: estimate };
        return { ...s, draft: requestDraft(request), requests: [request, ...s.requests], users: s.users.map(u => u.id === "demo" ? { ...u, tokens: u.tokens - estimate } : u), transactions: [{ id: crypto.randomUUID(), userId: "demo", amount: -estimate, reason: `Video demo · ${request.id.slice(0, 8)}`, createdAt: now }, ...s.transactions] };
      });
      setError(""); router.push(`/creator/project/${id}`);
    } catch { setError(t("Chưa tạo được video mẫu. Kiểm tra số dư hoặc tải lại trang.", "Could not create the sample. Check your balance or reload.")); }
  }
  if (projectId && ready && !generations.length) return <div className="studio-empty"><p>{t("Không tìm thấy dự án.", "Project not found.")}</p><button type="button" className="secondary-button" onClick={() => router.push("/creator/create")}>{t("Về workspace", "Back to workspace")}</button></div>;

  return <div className={`chat-workspace ${!prepared && !generations.length ? "chat-start" : ""}`}>
    <div className="chat-conversation" ref={conversationRef} aria-label={t("Nội dung dự án", "Project conversation")}>
      <div className="conversation-content">
        {!generations.length && !prepared && <div className="chat-empty"><p>{t("Biến đường link thành video.", "Turn a link into a video.")}</p><span>{t("Một nguồn sản phẩm. Một câu chuyện theo cách của bạn.", "One product source. A story told your way.")}</span><button type="button" className="text-button sample-link-button" onClick={() => update({ sourceUrl: "https://gamma.app", notes: t("Giới thiệu Gamma bằng 3 cảnh ngắn, dành cho người làm nội dung.", "Introduce Gamma in 3 short scenes for content creators."), preparedUrl: "" })}>{t("Thử với link mẫu", "Try a sample link")} <span aria-hidden="true">↗</span></button></div>}
        {generations.map(request => <section className="conversation-turn" key={request.id}>
          <div className="user-message"><a href={request.sourceUrl} target="_blank" rel="noreferrer">{request.sourceUrl}</a>{request.notes && <p>{request.notes}</p>}<ReferenceFiles files={request.references} /></div>
          <div className={`assistant-result video-view-${videoView}`}>
            <div className="result-heading"><h2>{t("Video của bạn", "Your videos")}</h2><span className="completion-tag">{t("Hoàn tất mẫu", "Sample ready")}</span></div>
            <div className="result-meta"><span>{videoModels.find(model => model.id === request.model)?.name} · {request.ratio} · {request.resolution} · {request.duration}s</span><span>{number(request.estimatedTokens)} token</span></div>
            <div className="result-videos">{Array.from({ length: request.count }, (_, index) => <article className="output-card" key={index}>
              <div className="output-card-heading"><strong>VIDEO {String(index + 1).padStart(2, "0")}</strong><span>MP4</span></div>
              <div className="output-player"><video controls playsInline preload="metadata" src="/media/leader-demo.mp4" poster="/media/sample-poster.jpg" style={{ aspectRatio: request.ratio.replace(":", " / ") }} aria-label={`${t("Video mẫu", "Sample video")} ${index + 1}`} /></div>
              <div className="output-card-footer"><span>{t("Video minh họa", "Sample video")} · 15s</span><a href="/media/leader-demo.mp4" download={`reviewlab-sample-${index + 1}.mp4`}>{t("Tải MP4", "Download MP4")} <span aria-hidden="true">↓</span></a></div>
            </article>)}</div>
            <div className="result-actions"><details className="result-prompt"><summary>{t("Xem prompt & cấu hình", "View prompt & settings")}</summary><p>{request.prompt}</p><strong>{t("Khung mở đầu", "Opening frame")}</strong><p>{request.opening}</p>{request.negativePrompt && <p>{t("Nội dung cần tránh", "Negative prompt")}: {request.negativePrompt}</p>}</details><button type="button" className="text-button" onClick={() => update(requestDraft(request))}>{t("Dùng lại", "Reuse")}</button></div>
            <p className="field-hint">{t("Clip mẫu 15 giây dùng để xem thử. Model và cấu hình đang mô phỏng.", "A shared 15-second preview clip. Models and settings are simulated.")}</p>
          </div>
        </section>)}
        {prepared && !generations.length && <section className="draft-preview"><div className="user-message"><span>{draft.sourceUrl}</span>{draft.notes && <p>{draft.notes}</p>}</div><div className="draft-opening" style={{ aspectRatio: draft.ratio.replace(":", " / ") }}><span>{t("KHUNG MỞ ĐẦU MẪU", "SAMPLE OPENING FRAME")}</span><strong>{new URL(draft.preparedUrl).hostname}</strong><p>{draft.opening}</p></div><details className="result-prompt" open><summary>{t("Prompt đề xuất", "Suggested prompt")}</summary><p>{draft.prompt}</p><button type="button" className="text-button" onClick={openDetails}>{t("Chỉnh sửa", "Edit")}</button></details></section>}
      </div>
    </div>
    <div className="chat-dock">
      <form ref={formRef} onSubmit={generate} className="chat-composer" aria-label={t("Tạo video", "Create video")}>
        <fieldset disabled={!ready || uploading}>
          <div className="composer-top-strip">
            <label className="composer-strip-control"><span>{t("Khung hình", "Frame")}</span><select aria-label={t("Tỷ lệ khung hình", "Aspect ratio")} value={draft.ratio} onChange={e => update({ ratio: e.target.value as Draft["ratio"] })}>{aspectRatios.map(ratio => <option key={ratio} value={ratio}>{ratio}</option>)}</select></label>
            <span className="composer-strip-cost" aria-live="polite" title={t("Token dự kiến (mẫu)", "Estimated tokens (sample)")}>{number(estimate)} <span>token</span></span>
          </div>
          <div className="composer-input-surface">
          <div className="chat-input-area">
            <label className="sr-only" htmlFor="source-url">{t("Link sản phẩm (bắt buộc)", "Product link (required)")}</label><input id="source-url" type="text" inputMode="url" value={draft.sourceUrl} onChange={e => update({ sourceUrl: e.target.value, productReview: null, preparedUrl: "" })} placeholder={t("Dán link sản phẩm · bắt buộc", "Paste a product link · required")} required />
            <textarea aria-label={t("Ghi chú", "Notes")} value={draft.notes} onChange={e => update({ notes: e.target.value, preparedUrl: "" })} placeholder={t("Thêm ý tưởng hoặc ghi chú…", "Add ideas or notes…")} rows={1} onKeyDown={e => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); formRef.current?.requestSubmit(); } }} />
            <ReferenceFiles files={draft.references} remove={removeReference} />
          </div>
          <div className="compact-composer-actions">
            <div className="attachment-action"><button type="button" className="attach-button" aria-label={t("Thêm ảnh hoặc tài liệu tham khảo", "Add reference images or documents")} title={t("Thêm ảnh hoặc tài liệu tham khảo", "Add reference images or documents")} onClick={() => uploadRef.current?.click()}><Plus size={21} /></button><input ref={uploadRef} className="file-upload-input" type="file" aria-label={t("Tệp tham khảo", "Reference files")} accept={referenceAccept} multiple onChange={upload} /><button type="button" className="composer-custom-button" disabled={!validSource} title={validSource ? t("Xem thông tin sản phẩm và cấu hình", "Review product information and configuration") : t("Nhập link sản phẩm hợp lệ để mở Chi tiết", "Enter a valid product link to open Details")} onClick={openDetails}>{t("Chi tiết", "Details")} ↗</button>{uploading && <small role="status">{t("Đang thêm tệp…", "Adding files…")}</small>}</div>
            <div className="compact-build-controls">
              <label className="compact-model-control"><span className="sr-only">{t("Model AI", "AI model")}</span><select aria-label={t("Model AI", "AI model")} value={draft.model} onChange={e => update({ model: e.target.value as Draft["model"] })}>{videoModels.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}</select></label>
              <button type="button" className="composer-mic-button" aria-label={t("Nhập bằng giọng nói", "Voice input")} title={t("Nhập bằng giọng nói", "Voice input")} aria-haspopup="dialog" onClick={openVoice}><Mic size={18} /></button>
              <button type="submit" className="compact-send-button" aria-label={t("Tạo video", "Create video")} title={`${t("Tạo video", "Create video")} · ${number(estimate)} token`} disabled={!validCountInput || !validSource || estimate > user.tokens || !user.active}><Play size={13} fill="currentColor" /><span>{t("Tạo", "Create")}</span></button>
            </div>
          </div>
          </div>
          <div className="composer-bottom-strip">
            <label className="composer-strip-control composer-count-control"><span>{t("Số lượng", "Count")}</span><input type="number" inputMode="numeric" min={1} step={1} required aria-label={t("Số lượng", "Video count")} value={countInput ?? draft.count} onFocus={() => setCountInput(String(draft.count))} onBlur={() => setCountInput(null)} onChange={e => { const text = e.target.value; const count = Number(text); setCountInput(text); if (Number.isSafeInteger(count) && count > 0 && Number.isSafeInteger(estimateTokens({ ...draft, count }))) update({ count }); }} /><span>video</span></label>
            <label className="composer-strip-control"><span>{t("Template", "Template")}</span><select aria-label={t("Template", "Template")} value={draft.style} onChange={e => update({ style: e.target.value as Draft["style"] })}><option value="cinematic">{t("Điện ảnh", "Cinematic")}</option><option value="animation">{t("Hoạt hình", "Animation")}</option><option value="realistic">{t("Chân thực", "Realistic")}</option><option value="minimal">{t("Tối giản", "Minimal")}</option></select></label>
            <label className="composer-strip-control"><span>{t("Thời gian", "Duration")}</span><select aria-label={t("Thời gian", "Duration")} value={draft.duration} onChange={e => update({ duration: Number(e.target.value) })}>{[5, 10, 15, 30, 60].map(n => <option key={n} value={n}>{n}s</option>)}</select></label>
          </div>
        </fieldset>
      </form>
      {error && <p role="alert" className="studio-error">{error}</p>}
      {estimate > user.tokens && <p className="studio-error">{t("Không đủ token mẫu. Giảm số lượng hoặc độ dài.", "Insufficient sample tokens. Reduce the count or duration.")}</p>}
      {!user.active && <p className="studio-error">{t("Tài khoản mẫu đang tạm dừng.", "The demo account is paused.")}</p>}
    </div>
    {voiceOpen && <Modal title={t("Nhập bằng giọng nói", "Voice input")} close={() => setVoiceOpen(false)}>
      <div className="editor-form">
        <p className="voice-demo-hint">{t("Bản mô phỏng: dùng đoạn nói mẫu để thử thêm ghi chú.", "Demo: use a sample transcript to try adding voice notes.")}</p>
        <label>{t("Ngôn ngữ nói", "Spoken language")}<select aria-label={t("Ngôn ngữ nói", "Spoken language")} value={voiceLanguage} onChange={e => { setVoiceLanguage(e.target.value); setVoiceText(""); }}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label>
        <button type="button" className="voice-sample-button" onClick={() => setVoiceText(voiceLanguage === "vi" ? "Tạo video giới thiệu sản phẩm với nhịp nhanh, ánh sáng tự nhiên và kết thúc bằng lời mời tìm hiểu thêm." : "Create a product introduction with a brisk pace, natural lighting, and an invitation to learn more at the end.")}><Mic size={18} /><span>{t("Thử đoạn nói mẫu", "Try a sample transcript")}</span></button>
        <label>{t("Nội dung nhận được", "Transcript")}<textarea aria-label={t("Nội dung nhận được", "Transcript")} rows={3} value={voiceText} onChange={e => setVoiceText(e.target.value)} placeholder={t("Nội dung sẽ được thêm vào ghi chú…", "This text will be added to your notes…")} /></label>
        <div className="dialog-actions"><button type="button" className="primary-button" disabled={!voiceText.trim()} onClick={useVoiceNotes}>{t("Thêm vào ghi chú", "Add to notes")}</button></div>
      </div>
    </Modal>}
    {custom && <Modal title={t("Chi tiết dự án", "Project details")} close={closeDetails}><ProjectDetails review={draft.productReview} confirmed={productIsConfirmed(draft)} files={draft.references} error={detailError} phase={processing.phase} prepare={() => { setDetailError(""); void processing.start(prepareProduct); }} change={changeProduct} confirm={confirmProduct} removeFile={removeReference}><div className="editor-form"><button type="button" className="secondary-button" disabled={!draft.sourceUrl.trim()} onClick={previewPrompt}>{t("Tạo prompt từ link", "Prepare prompt from link")}</button><label>Prompt<textarea aria-label="Prompt" value={draft.prompt} onChange={e => update({ prompt: e.target.value })} placeholder={t("Nhấn Tạo prompt từ link để nhận đề xuất.", "Use Prepare prompt from link to get a suggestion.")} rows={6} /></label><label>{t("Khung mở đầu", "Opening frame")}<textarea aria-label={t("Khung mở đầu", "Opening frame")} value={draft.opening} onChange={e => update({ opening: e.target.value })} rows={3} /></label><div className="config-grid"><label>{t("Độ phân giải", "Resolution")}<select aria-label={t("Độ phân giải", "Resolution")} value={draft.resolution} onChange={e => update({ resolution: e.target.value as Draft["resolution"] })}><option>1080p</option><option>720p</option></select></label><label>{t("Ngôn ngữ video", "Video language")}<select aria-label={t("Ngôn ngữ video", "Video language")} value={draft.outputLanguage} onChange={e => update({ outputLanguage: e.target.value as Draft["outputLanguage"] })}><option value="vi">Tiếng Việt</option><option value="en">English</option></select></label><label>{t("Máy quay", "Camera")}<select aria-label={t("Máy quay", "Camera")} value={draft.camera} onChange={e => update({ camera: e.target.value as Draft["camera"] })}><option value="auto">{t("Tự động", "Automatic")}</option><option value="static">{t("Cố định", "Static")}</option><option value="pan">{t("Lia máy", "Pan")}</option></select></label></div><label>{t("Nội dung cần tránh", "Negative prompt")}<textarea aria-label={t("Nội dung cần tránh", "Negative prompt")} value={draft.negativePrompt} onChange={e => update({ negativePrompt: e.target.value })} rows={2} /></label><div className="dialog-actions"><button type="button" className="primary-button" onClick={closeDetails}>{t("Xong", "Done")}</button></div></div></ProjectDetails></Modal>}
  </div>;
}
