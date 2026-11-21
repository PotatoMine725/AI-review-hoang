# ADR-0005: Cấu trúc repo và nguyên tắc mở rộng

- **Trạng thái:** Đề xuất (chốt ở buổi review thứ Sáu 09/10)
- **Ngày:** 2026-10-05
- **Người đề xuất:** @PotatoMine725
- **Người quyết định:** team lead @VV6505 (decision-log #12)

> Số 0001–0004 được dành cho các ADR đã giao trong kế hoạch tuần 1:
> ADR-001 crawl tool, ADR-002 LLM provider, ADR-003 render engine, ADR-004 avatar + TTS.

## Bối cảnh
- Stack lõi đã chốt: Next.js cho web, Supabase cho Auth/DB/Storage, Python 3.12 + FastAPI cho API nghiệp vụ. API và worker xử lý nền chạy thành hai tiến trình riêng trong cấu trúc `services/worker/` hiện có; chưa cần thêm service chỉ để tách hai tiến trình.
- **Quyết định crawl/LLM đã chốt:** ADR-0001/0002 đã chốt Crawl4AI như thư viện và Gemini `gemini-3.5-flash-lite` qua `google-genai`/adapter mỏng; embedding/RAG hoãn sau MVP. ADR-003/004 (render/TTS) còn mở; trạng thái của chính ADR-0005 không thay đổi. Một số lựa chọn kéo theo thay đổi cấu trúc:
  - Render engine: HyperFrames và Revideo chạy trên Node/TypeScript, còn FFmpeg/MoviePy chạy trên Python. Chọn Node thì cần **một service thứ hai, khác ngôn ngữ**.
  - LLM, avatar, TTS: chỉ là API bên ngoài, đổi provider không được làm thay đổi cấu trúc thư mục.
- PRD §60 yêu cầu "Video Provider Adapter, không lock vào một video API". NFR-08 của Module 1 yêu cầu đổi model LLM bằng config, không sửa code; MVP không có embedding.
- Team đang dùng split repo (FE/BE), trong khi kế hoạch tuần 1 ghi monorepo. Cấu trúc phải để ngỏ khả năng gộp lại.

## Các lựa chọn
| Lựa chọn | Ưu | Nhược |
|---|---|---|
| A. Worker ở thư mục gốc repo BE | Đơn giản nhất | Thêm service thứ hai thì phải dời cấu trúc; CI khó lọc theo service |
| B. `services/<tên>/`, mỗi service tự chứa | Thêm service = thêm thư mục; CI lọc theo path; khớp với cây monorepo trong brief | Thêm 1 cấp thư mục |
| C. Khung đầy đủ ngay (workspace, docker-compose, base class cho provider) | Sẵn sàng cho mọi thứ | Tạo cấu trúc chưa ai dùng; khó sửa khi ADR-001…004 chốt khác dự kiến |

## Quyết định
Chọn **B**, kèm 4 nguyên tắc:

1. **Service tự chứa.** Mỗi `services/<tên>/` có trình quản lý dependency riêng (uv, pnpm, …), `.env.example`, README và
   workflow CI riêng `.github/workflows/<tên>.yml` lọc theo `services/<tên>/**`. Các service không import code của nhau.
2. **Giao tiếp qua hợp đồng có tài liệu.** Chỉ có 3 kênh:
   - HTTP: FE gọi FastAPI cho Product/PKB/job và các thao tác nghiệp vụ cần backend tin cậy; OpenAPI và tài liệu ở `docs/specs/api-contract.md`. Next.js Route Handler nếu dùng chỉ làm proxy, không có lớp nghiệp vụ thứ hai;
   - DB: schema trong `supabase/migrations/`;
   - Queue: đề xuất worker poll `generation_jobs` trong Postgres, claim nguyên tử bằng `FOR UPDATE SKIP LOCKED`, không thêm Redis/Celery/pgmq ở Sprint 1. BE hoàn thiện ADR cho payload, lease, retry và phục hồi; chưa xác nhận queue đã triển khai.

   Nhờ vậy đổi ngôn ngữ hay framework của một bên không làm vỡ bên kia.
3. **Provider nằm sau adapter, chọn bằng config.** Code nghiệp vụ gọi interface của chính mình (ví dụ "sinh giọng nói", "render video"),
   không gọi SDK của provider trực tiếp. Provider được chọn qua biến môi trường hoặc config. Interface được viết **khi có provider đầu tiên**,
   không viết trước.
4. **Không dựng trước cấu trúc chưa dùng.** Workspace, docker-compose, reusable workflow chỉ thêm khi có service thứ hai cần đến.

### Cách thêm một service (ví dụ `render` bằng Node)
1. Tạo `services/render/` với `package.json` (pnpm), `.env.example`, README.
2. Copy `.github/workflows/worker.yml` thành `render.yml`, đổi path và các bước cài đặt/lint.
3. Thêm owner vào `.github/CODEOWNERS`. Thêm endpoint (nếu có) vào `docs/specs/api-contract.md`.
4. Ghi vào `docs/logs/decision-log.md`.

### Nếu sau này gộp thành monorepo
Cây thư mục BE đã khớp với brief (`services/`, `supabase/`, `docs/`). Repo FE được đưa vào bằng:
```bash
git subtree add --prefix=apps/web https://github.com/PotatoMine725/AI-review-FE.git main
```
Lệnh này giữ nguyên lịch sử commit. Sau đó gộp `.github/` của 2 repo lại và archive repo FE.

## Hệ quả
- Dễ hơn: thêm service khác ngôn ngữ sau ADR-003; đổi provider LLM/TTS/avatar; gộp monorepo.
- Khó hơn: lệnh chạy worker dài hơn một cấp thư mục (`cd services/worker`).
- Việc cần làm tiếp: khi chốt ADR-001…004, cập nhật mục "Bối cảnh" của ADR này nếu có service mới.
