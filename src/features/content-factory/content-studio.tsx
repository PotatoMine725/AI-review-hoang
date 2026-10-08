"use client";

import Link from "next/link";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { approvedKnowledge, createMockContent } from "./model";
import { useWorkspace } from "./workspace-provider";
import { confirmDiscard, useUnsavedChanges } from "./use-unsaved-changes";

export function ContentStudio({ productPath = "/products" }: { productPath?: string }) {
  const { projects, selectedId, setSelectedId, updateProject, ready } = useWorkspace();
  const selected = projects.find(p => p.id === selectedId)!;
  const approved = approvedKnowledge(selected);
  const [tab, setTab] = useState<"hook" | "script" | "caption">("hook");
  const [audience, setAudience] = useState("Content creators");
  const [platform, setPlatform] = useState("TikTok / Reels");
  const [message, setMessage] = useState("");
  const [dirty, setDirty] = useState(false);
  const [editorRevision, setEditorRevision] = useState(0);
  const labels = { hook: "Hook", script: "Kịch bản", caption: "Caption" };
  function run(action: () => void) { try { action(); setMessage("Đã lưu content mock trong trình duyệt."); return true; } catch (error) { setMessage(error instanceof Error ? error.message : "Không thể lưu."); return false; } }
  function exportContent() {
    if (!selected.content) return;
    const content = selected.content;
    const url = URL.createObjectURL(new Blob([`# ${selected.name}\n\nDEMO TEMPLATE — not AI generated. PKB v${content.knowledgeVersion}\n\n## Hook\n${content.hook}\n\n## Script\n${content.script}\n\n## Caption\n${content.caption}`], { type: "text/markdown;charset=utf-8" }));
    const a = document.createElement("a"); a.href = url; a.download = "review-content-demo.md"; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return <section className="studio-section">
    <div className="section-heading"><div><h2>Content Factory</h2><p>Template demo, không mô phỏng job AI. Luôn dùng một snapshot PKB đã duyệt.</p></div><div className="product-selector"><label htmlFor="selected-product">Sản phẩm</label><select id="selected-product" disabled={!ready} value={selectedId} onChange={e => { if (confirmDiscard(dirty) && run(() => setSelectedId(e.target.value))) setDirty(false); }}>{projects.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}</select></div></div>
    <div className="content-panel">
      <p className="content-pkb">{approved ? `PKB hiện tại: v${approved.version} · approved · English` : "Chưa có PKB được merchant duyệt."} <Link href={`${productPath}/${selected.id}`}>Review PKB ↗</Link></p>
      <div className="generation-settings"><div><label htmlFor="content-audience">Đối tượng</label><select id="content-audience" value={audience} onChange={e => setAudience(e.target.value)}><option>Content creators</option><option>Students</option><option>Product teams</option></select></div><div><label htmlFor="content-platform">Nền tảng</label><select id="content-platform" value={platform} onChange={e => setPlatform(e.target.value)}><option>TikTok / Reels</option><option>YouTube Shorts</option></select></div></div>
      {selected.content && <p className="demo-note">Content đang lưu dùng PKB v{selected.content.knowledgeVersion}.{selected.content.knowledgeVersion !== approved?.version && " Đã có PKB mới; tạo lại nếu muốn dùng phiên bản hiện tại."}</p>}
      <div className="output-tabs" role="tablist" aria-label="Loại nội dung">{(["hook", "script", "caption"] as const).map(key => <button key={key} id={`tab-${key}`} type="button" role="tab" aria-selected={tab === key} aria-controls="content-output" className={tab === key ? "active" : ""} onClick={() => { if (key !== tab && confirmDiscard(dirty)) { setDirty(false); setTab(key); } }}>{labels[key]}</button>)}</div>
      <div role="tabpanel" id="content-output" aria-labelledby={`tab-${tab}`}>
        {selected.content ? <ContentEditor key={`${selected.id}-${tab}-${selected.content.knowledgeVersion}-${editorRevision}-${selected.content[tab]}`} text={selected.content[tab]} label={`Chỉnh sửa ${labels[tab]}`} onDirty={setDirty} onSave={text => run(() => updateProject(selected.id, p => ({ ...p, content: { ...p.content!, [tab]: text } })))} /> : <div className="content-empty"><h3>Chưa có nội dung</h3><p>Duyệt PKB trước khi tạo template tiếng Anh.</p></div>}
      </div>
      <div className="content-actions"><Button disabled={!ready || !approved} onClick={() => { if (confirmDiscard(dirty) && run(() => { updateProject(selected.id, p => ({ ...p, content: createMockContent(p, audience, platform) })); setTab("script"); })) { setDirty(false); setEditorRevision(value => value + 1); } }}>{selected.content ? "Tạo lại template" : "Tạo template"}</Button><div><Button variant="outline" disabled={!selected.content || dirty} onClick={async () => { try { await navigator.clipboard.writeText(selected.content![tab]); setMessage("Đã sao chép."); } catch { setMessage("Không truy cập được clipboard. Hãy sao chép trực tiếp từ ô nội dung."); } }}>Sao chép</Button><Button variant="outline" disabled={!selected.content || dirty} onClick={exportContent}>Tải Markdown</Button></div></div>
      {message && <p role="status" className="notice">{message}</p>}
    </div>
  </section>;
}
function ContentEditor({ text, label, onSave, onDirty }: { text: string; label: string; onSave: (value: string) => boolean; onDirty: (value: boolean) => void }) {
  const [value, setValue] = useState(text);
  useUnsavedChanges(value !== text);
  return <><Textarea aria-label={label} value={value} onChange={e => { setValue(e.target.value); onDirty(e.target.value !== text); }} className="output-editor" /><Button variant="outline" disabled={value === text} onClick={() => { if (onSave(value)) onDirty(false); }}>Lưu nội dung</Button></>;
}
