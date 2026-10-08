"use client";
import { LoaderCircle } from "lucide-react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  changeJob,
  createMockProject,
  validAffiliateUrl,
  type IntakeDraft,
} from "./model";
import { useWorkspace } from "./workspace-provider";
import { useUnsavedChanges } from "./use-unsaved-changes";
import { IntakeStepper } from "./intake-stepper";
import { openUpload, storeUpload } from "./uploads";
const empty: IntakeDraft = {
  website: "",
  affiliate: "",
  name: "",
  tagline: "",
  pricing: "",
  features: [""],
  forbiddenClaims: "",
  logo: "",
  color: "#333333",
  uploads: [],
};
export function Onboarding() {
  const workspace = useWorkspace();
  return workspace.ready ? (
    <Intake initial={workspace.intakeDraft ?? empty} />
  ) : (
    <p role="status">Đang khôi phục bản nháp…</p>
  );
}
function Intake({ initial }: { initial: IntakeDraft }) {
  const { addProject, updateProject, saveIntake } = useWorkspace();
  const router = useRouter();
  const [form, setForm] = useState(() => structuredClone(initial));
  const [dirty, setDirty] = useState(false),
    [busy, setBusy] = useState(false);
  const [error, setError] = useState(""),
    [notice, setNotice] = useState("");
  const [job, setJob] = useState<string | null>(null),
    [stage, setStage] = useState(0),
    [waf, setWaf] = useState(false);
  useUnsavedChanges(dirty);
  function field<K extends keyof IntakeDraft>(key: K, value: IntakeDraft[K]) {
    setForm((current) => ({ ...current, [key]: value }));
    setDirty(true);
  }
  function run(action: () => void) {
    try {
      action();
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể lưu.");
    }
  }
  async function upload(files: FileList | null) {
    if (!files?.length) return;
    setBusy(true);
    try {
      if (form.uploads.length + files.length > 5)
        throw new Error("Tối đa 5 file × 5 MB.");
      const added = [];
      for (const file of Array.from(files)) added.push(await storeUpload(file));
      field("uploads", [...form.uploads, ...added]);
      setError("");
    } catch (cause) {
      setError(
        cause instanceof Error ? cause.message : "Không lưu được tài liệu.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function readLogo(file?: File) {
    if (!file) return;
    try {
      if (
        !["image/png", "image/svg+xml"].includes(file.type) ||
        file.size > 300_000
      )
        throw new Error("Logo SVG/PNG tối đa 300 KB.");
      const value = await new Promise<string>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(String(reader.result));
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
      field("logo", value);
      setError("");
    } catch {
      setError("Không đọc được logo. Chọn SVG/PNG tối đa 300 KB.");
    }
  }
  function start() {
    run(() => {
      if (!validAffiliateUrl(form.website))
        throw new Error(
          "Website URL bắt buộc và phải có định dạng HTTP/HTTPS hợp lệ.",
        );
      if (!validAffiliateUrl(form.affiliate))
        throw new Error(
          "Merchant affiliate URL bắt buộc và phải có định dạng HTTP/HTTPS hợp lệ.",
        );
      if (!/^#[0-9a-f]{6}$/i.test(form.color))
        throw new Error("Màu thương hiệu cần mã hex, ví dụ #333333.");
      if (form.logo && !/^data:image\/(png|svg\+xml);base64,/.test(form.logo)) {
        const url = new URL(form.logo);
        if (!["http:", "https:"].includes(url.protocol))
          throw new Error("Link logo không hợp lệ.");
      }
      const project = createMockProject(form.website, form.affiliate);
      project.name = form.name.trim() || project.name;
      project.merchantInput = structuredClone(form);
      addProject(changeJob(project, "running"));
      setDirty(false);
      setStage(0);
      setWaf(false);
      setJob(project.id);
    });
  }
  const uploads = (
    <div
      className="upload-zone"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        if (!busy) void upload(e.dataTransfer.files);
      }}
    >
      <label htmlFor="intake-files">Kéo thả PDF / ảnh hoặc chọn tài liệu</label>
      <input
        id="intake-files"
        type="file"
        multiple
        accept="application/pdf,image/png,image/jpeg,image/webp"
        disabled={busy}
        onChange={(e) => {
          void upload(e.target.files);
          e.target.value = "";
        }}
      />
      <p>
        Fallback cho website sau đăng nhập / WAF. Tối đa 5 file × 5 MB; lưu
        bytes trong IndexedDB local.
      </p>
      {form.uploads.map((file) => (
        <div className="upload-file" key={file.id}>
          <Button
            variant="ghost"
            onClick={() => {
              void openUpload(file).catch((cause) => setError(cause.message));
            }}
          >
            {file.name} · {Math.ceil(file.size / 1024)} KB
          </Button>
          <Button
            variant="ghost"
            onClick={() =>
              field(
                "uploads",
                form.uploads.filter((item) => item.id !== file.id),
              )
            }
          >
            Bỏ
          </Button>
        </div>
      ))}
    </div>
  );
  return (
    <>
      <div className="page-heading">
        <div>
          <p className="eyebrow">MERCHANT · ONBOARDING</p>
          <h1>Thêm sản phẩm mới</h1>
          <p>Ưu tiên Merchant; xác nhận các khác biệt tại Review PKB.</p>
        </div>
      </div>
      <IntakeStepper current={job ? 2 : 1} />
      <p className="review-demo-banner">
        Mock local · Không gọi website hoặc AI. Điều khiển các bước bằng tay để
        thử UI.
      </p>
      <section className="portal-panel intake-form">
        <div className="intake-grid">
          {(["website", "affiliate"] as const).map((key) => (
            <div key={key}>
              <label htmlFor={`intake-${key}`}>
                {key === "website"
                  ? "Website URL *"
                  : "Merchant affiliate URL *"}
              </label>
              <Input
                id={`intake-${key}`}
                type="url"
                value={form[key]}
                onChange={(e) => field(key, e.target.value)}
                placeholder="https://product.example"
              />
            </div>
          ))}
        </div>
        <details className="intake-optional">
          <summary>Thông tin bổ sung (không bắt buộc)</summary>
          <div className="intake-grid">
            {(["name", "tagline"] as const).map((key) => (
              <div key={key}>
                <label htmlFor={`intake-${key}`}>
                  {key === "name" ? "Tên sản phẩm" : "Tagline"}
                </label>
                <Input
                  id={`intake-${key}`}
                  value={form[key]}
                  onChange={(e) => field(key, e.target.value)}
                />
              </div>
            ))}
          </div>
          <label htmlFor="intake-pricing">Giá / khuyến mãi nguyên văn</label>
          <Textarea
            id="intake-pricing"
            value={form.pricing}
            onChange={(e) => field("pricing", e.target.value)}
          />
          <p>
            Nhập giá, tiền tệ, chu kỳ, điều kiện; kiểm tra lại số tiền trong
            PKB.
          </p>
          <fieldset>
            <legend>Tính năng chính</legend>
            {form.features.map((value, i) => (
              <div key={i} className="upload-file">
                <Input
                  aria-label={`Tính năng ${i + 1}`}
                  value={value}
                  onChange={(e) =>
                    field(
                      "features",
                      form.features.map((item, index) =>
                        index === i ? e.target.value : item,
                      ),
                    )
                  }
                />
                <Button
                  variant="outline"
                  disabled={form.features.length === 1}
                  onClick={() =>
                    field(
                      "features",
                      form.features.filter((_, index) => index !== i),
                    )
                  }
                >
                  Xóa
                </Button>
              </div>
            ))}
            <Button
              variant="outline"
              onClick={() => field("features", [...form.features, ""])}
            >
              Thêm tính năng
            </Button>
          </fieldset>
          <label htmlFor="intake-forbidden">Forbidden claims</label>
          <Textarea
            id="intake-forbidden"
            value={form.forbiddenClaims}
            onChange={(e) => field("forbiddenClaims", e.target.value)}
          />
          <div className="intake-grid">
            <div>
              <label htmlFor="intake-logo">Logo URL hoặc SVG/PNG</label>
              <Input
                id="intake-logo"
                value={form.logo.startsWith("data:") ? "" : form.logo}
                onChange={(e) => field("logo", e.target.value)}
              />
              <input
                aria-label="Tải logo"
                type="file"
                accept="image/png,image/svg+xml"
                onChange={(e) => {
                  void readLogo(e.target.files?.[0]);
                }}
              />
              {form.logo && (
                <Image
                  unoptimized
                  src={form.logo}
                  alt="Logo đã chọn"
                  width={48}
                  height={48}
                />
              )}
            </div>
            <div>
              <label htmlFor="intake-color">Màu thương hiệu (hex)</label>
              <Input
                id="intake-color"
                value={form.color}
                onChange={(e) => field("color", e.target.value)}
              />
            </div>
          </div>
        </details>
        {!waf && uploads}
        <div className="portal-actions">
          <Button disabled={busy} onClick={start}>
            Bắt đầu phân tích
          </Button>
          <Button
            variant="outline"
            disabled={busy || !dirty}
            onClick={() =>
              run(() => {
                saveIntake(form);
                setDirty(false);
                setNotice("Đã lưu bản nháp onboarding.");
              })
            }
          >
            Lưu bản nháp
          </Button>
        </div>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        {notice && (
          <p role="status" className="notice">
            {notice}
          </p>
        )}
      </section>
      <Dialog
        open={!!job}
        onOpenChange={(open) => {
          if (!open) {
            setJob(null);
            setWaf(false);
          }
        }}
      >
        <DialogContent>
          <DialogTitle>
            {waf ? "Website bị chặn (mô phỏng)" : "Thu thập thông tin (mock)"}
          </DialogTitle>
          <DialogDescription>
            Đóng cửa sổ vẫn giữ job trong dashboard. Không có tiến độ backend
            thực.
          </DialogDescription>
          {waf ? (
            <>
              <p className="report-box">
                WAF / trang yêu cầu đăng nhập: upload PDF hoặc ảnh để tiếp tục.
              </p>
              {uploads}
              <Button
                disabled={!form.uploads.length || busy}
                onClick={() =>
                  run(() => {
                    updateProject(job!, (p) => {
                      const next = changeJob(p, "running");
                      return {
                        ...next,
                        merchantInput: structuredClone(form),
                        job: {
                          ...next.job,
                          step: "Phân tích tài liệu thay thế (mock)",
                        },
                      };
                    });
                    setWaf(false);
                    setStage(2);
                    setDirty(false);
                  })
                }
              >
                Phân tích tài liệu mẫu
              </Button>
            </>
          ) : (
            <>
              <LoaderCircle className="spin" aria-label="Đang phân tích mock" />
              <ol className="processing-steps">
                {[
                  "Kết nối website",
                  "Tìm sitemap / trang sản phẩm",
                  "Trích xuất thông tin thành PKB",
                ].map((label, i) => (
                  <li
                    key={label}
                    aria-current={stage === i ? "step" : undefined}
                  >
                    {i < stage ? "✓" : i === stage ? "◉" : "○"} {label}
                  </li>
                ))}
              </ol>
              <progress max={3} value={stage + 1} aria-label="Tiến độ mock" />
              <p className="demo-note">
                Bước {stage + 1}/3 · minh họa thủ công
              </p>
              <div className="portal-actions">
                <Button
                  onClick={() =>
                    run(() => {
                      if (stage < 2) {
                        updateProject(job!, (p) => ({
                          ...p,
                          job: {
                            ...p.job,
                            step:
                              stage === 0
                                ? "Đọc sitemap (mock)"
                                : "Bóc tách PKB (mock)",
                          },
                        }));
                        setStage(stage + 1);
                      } else {
                        updateProject(job!, (p) => changeJob(p, "completed"));
                        setDirty(false);
                        router.push(`/merchant/products/${job}`);
                        setJob(null);
                      }
                    })
                  }
                >
                  {stage < 2
                    ? "Bước tiếp theo (mock)"
                    : "Hoàn tất và review PKB"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() =>
                    run(() => {
                      updateProject(job!, (p) => {
                        const next = changeJob(p, "failed");
                        return {
                          ...next,
                          job: {
                            ...next.job,
                            error:
                              "waf_challenge: upload tài liệu thay thế (mock)",
                          },
                        };
                      });
                      setWaf(true);
                    })
                  }
                >
                  Mô phỏng WAF
                </Button>
              </div>
            </>
          )}
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
