"""Tự quay clip thao tác (demo) bằng Playwright, thay cho quay tay.

LLM KHÔNG điều khiển trình duyệt lúc quay. Quy trình:

1. `generate`: GPT đọc DOM trang + fact PKB, sinh MỘT action-script JSON (`schema.ActionScript`).
   Script được chạy thử (dry-run) trên trang thật; lỗi selector thì gửi lại cho GPT sửa.
2. `record`: Playwright chạy lại script y hệt mỗi lần (con trỏ giả, gõ chậm, `recordVideo`),
   ra MP4 + đoạn `assets.json` (`produce.assets.Asset`) để khâu dựng dùng ngay.
"""
