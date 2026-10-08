"use client";
import Link from "next/link";
import Image from "next/image";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { useWorkspace } from "../content-factory/workspace-provider";
import {
  changeJob,
  approvedKnowledge,
  latestKnowledge,
} from "../content-factory/model";
import { useVideos } from "../video-qa/provider";
import { changeRender } from "../video-qa/model";
export function Pipeline() {
  const { projects, updateProject, setSelectedId } = useWorkspace();
  const { assets, updateVideo } = useVideos();
  const [error, setError] = useState("");
  function run(action: () => void) {
    try {
      action();
      setError("");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không lưu được job.");
    }
  }
  return (
    <>
      <section className="portal-panel portal-spacing">
        <h2>Pipeline / Job Monitor</h2>
        <p className="demo-note">
          Crawl → Extract → Render. Tiến độ minh họa theo trạng thái; dùng nút
          để mô phỏng, chưa có tiến độ backend.
        </p>
        <div className="pipeline-grid">
          {projects.map((p) => (
            <article className="job-card" key={p.job.id}>
              <strong>{p.name} · Crawl / Trích xuất PKB</strong>
              <p>
                {p.job.status} · {p.job.step} ·{" "}
                {p.job.status === "completed"
                  ? "100%"
                  : p.job.status === "running"
                    ? "50%"
                    : "0%"}{" "}
                (mock)
              </p>
              <progress
                max={100}
                value={
                  p.job.status === "completed"
                    ? 100
                    : p.job.status === "running"
                      ? 50
                      : 0
                }
                aria-label={`Tiến độ mock ${p.name}`}
              />
              {p.job.error && <p className="form-error">{p.job.error}</p>}
              {["queued", "failed"].includes(p.job.status) && (
                <Button
                  variant="outline"
                  onClick={() =>
                    run(() =>
                      updateProject(p.id, (item) => changeJob(item, "running")),
                    )
                  }
                >
                  {p.job.status === "failed" ? "Thử lại" : "Bắt đầu"} crawl mock
                </Button>
              )}
              {p.job.status === "running" && (
                <div className="portal-actions">
                  <Button
                    variant="outline"
                    onClick={() =>
                      run(() =>
                        updateProject(p.id, (item) =>
                          changeJob(item, "completed"),
                        ),
                      )
                    }
                  >
                    Hoàn tất crawl mock
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() =>
                      run(() =>
                        updateProject(p.id, (item) =>
                          changeJob(item, "failed"),
                        ),
                      )
                    }
                  >
                    Mô phỏng lỗi crawl
                  </Button>
                </div>
              )}
            </article>
          ))}
          {assets.map((a) => (
            <article className="job-card" key={a.review.id}>
              <strong>{a.review.product} · Render</strong>
              <p>
                {a.render?.status ?? "completed"} · {a.render?.step} ·{" "}
                {a.render?.status === "completed"
                  ? "100%"
                  : a.render?.status === "running"
                    ? "50%"
                    : "0%"}{" "}
                (mock)
              </p>
              <progress
                max={100}
                value={
                  a.render?.status === "completed"
                    ? 100
                    : a.render?.status === "running"
                      ? 50
                      : 0
                }
                aria-label={`Tiến độ render mock ${a.review.product}`}
              />
              {a.render?.error && (
                <p className="form-error">{a.render.error}</p>
              )}
              {a.render && ["queued", "failed"].includes(a.render.status) && (
                <Button
                  variant="outline"
                  onClick={() =>
                    run(() =>
                      updateVideo(a.review.id, (current) =>
                        changeRender(current, "running"),
                      ),
                    )
                  }
                >
                  {a.render.status === "failed"
                    ? "Thử lại render mock"
                    : "Bắt đầu render mock"}
                </Button>
              )}
              {a.render?.status === "running" && (
                <div className="portal-actions">
                  <Button
                    onClick={() =>
                      run(() =>
                        updateVideo(a.review.id, (current) =>
                          changeRender(current, "completed"),
                        ),
                      )
                    }
                  >
                    Hoàn tất render mock
                  </Button>
                  <Button
                    variant="outline"
                    onClick={() =>
                      run(() =>
                        updateVideo(a.review.id, (current) =>
                          changeRender(current, "failed"),
                        ),
                      )
                    }
                  >
                    Mô phỏng lỗi render
                  </Button>
                </div>
              )}
            </article>
          ))}
        </div>
      </section>
      <section className="portal-panel portal-spacing">
        <h2>Sản phẩm</h2>
        <div className="table-scroll">
          <table className="leader-table">
            <thead>
              <tr>
                <th>Sản phẩm / domain</th>
                <th>PKB</th>
                <th>Video sẵn sàng</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {projects.map((p) => (
                <tr key={p.id}>
                  <td>
                    <div className="product-cell">
                      <Image
                        className="product-logo"
                        unoptimized
                        src={p.merchantInput?.logo || "/media/product-mark.svg"}
                        alt={`Logo ${p.name}`}
                        width={32}
                        height={32}
                      />
                      <div>
                        <strong>{p.name}</strong>
                        <small>{new URL(p.url).hostname}</small>
                      </div>
                    </div>
                  </td>
                  <td>{latestKnowledge(p)?.status || "Chưa có"}</td>
                  <td>
                    {
                      assets.filter(
                        (a) =>
                          a.productId === p.id &&
                          a.render?.status === "completed" &&
                          a.status === "approved",
                      ).length
                    }
                  </td>
                  <td>
                    <div className="row-actions">
                      <Link href={`/merchant/products/${p.id}`}>
                        Review PKB
                      </Link>
                      <Link
                        href="/merchant/content"
                        aria-disabled={!approvedKnowledge(p)}
                        onClick={(e) => {
                          if (!approvedKnowledge(p)) {
                            e.preventDefault();
                            setError("Duyệt PKB trước khi tạo video.");
                          } else
                            try {
                              setSelectedId(p.id);
                            } catch (cause) {
                              e.preventDefault();
                              setError(
                                cause instanceof Error
                                  ? cause.message
                                  : "Không chọn được sản phẩm.",
                              );
                            }
                        }}
                      >
                        Tạo video
                      </Link>
                      <Link href="/merchant/campaigns">Campaign</Link>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
    </>
  );
}
