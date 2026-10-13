# AI-review-FE

Web app của **AI Review Content Factory & Affiliate Network**: giao diện mock Creator tạo video và Admin quản lý người dùng, token, gói đăng ký, PKB.

Backend, schema DB và tài liệu (PRD, ADR, log) nằm ở [AI-review-BE](https://github.com/PotatoMine725/AI-review-BE).

## Stack
Next.js (App Router) + TypeScript + Tailwind CSS + shadcn/ui, pnpm.

## Cấu trúc

```
AI-review-FE/
├── src/
│   ├── app/             # App Router: layout.tsx, page.tsx, globals.css
│   ├── components/ui/   # component shadcn/ui (thêm bằng: pnpm dlx shadcn@latest add <tên>)
│   ├── features/        # (khi có) code theo tính năng: features/<module>/
│   └── lib/
│       ├── utils.ts
│       ├── api/         # (khi có) MỌI lời gọi HTTP tới worker/service đi qua đây
│       └── supabase/    # (khi có) client Supabase server + browser
├── components.json      # cấu hình shadcn/ui
├── .env.example
└── .github/             # CI (ci.yml), PR/issue template, CODEOWNERS
```

## Chạy local

Yêu cầu: Node.js 24, pnpm (phiên bản trong `packageManager` của `package.json`).

```bash
pnpm install
cp .env.example .env.local    # tùy chọn khi cấu hình kết nối; giao diện mock không cần backend
pnpm dev                      # http://localhost:3000
```

## Mô tả giao diện

[Mô tả giao diện mock Creator và Admin](https://github.com/PotatoMine725/AI-review-BE/blob/dev/docs/specs/web-creator-admin-mock.md) nằm ở repo BE.

## Tài liệu

- [CONTRIBUTING.md](CONTRIBUTING.md): Git flow, commit, PR, Definition of Done
- [AI-review-BE/docs](https://github.com/PotatoMine725/AI-review-BE/tree/dev/docs): PRD, API contract và tài liệu backend
