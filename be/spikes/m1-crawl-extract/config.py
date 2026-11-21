"""Cấu hình bước 2: model, bảng giá, giới hạn chi phí.

Giá tra cứu 06/10/2026 tại https://ai.google.dev/gemini-api/docs/pricing (gói trả phí, Standard).
Khớp với giá trong spec (tra 05/10/2026). Giá output đã gồm thinking token.
"""

PRICES_CHECKED_AT = "2026-10-06"

# model id → giá USD / 1M token
MODELS: dict[str, dict[str, float]] = {
    "gemini-3.1-flash-lite": {"input": 0.25, "output": 1.50},
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
}

TOP_PAGES = 10  # mode batch: gom N trang điểm cao nhất vào 1 lời gọi. Mode per_page: mọi trang đã crawl
RAW_PAGE_TYPES = ("pricing",)  # page_type gửi raw markdown (fit_markdown làm rơi thẻ giá)
# Chặn trên output mỗi lời gọi (gồm cả thinking token); cũng dùng để tính chi phí xấu nhất.
MAX_OUTPUT_TOKENS = {"per_page": 4096, "batch": 16384}
BUDGET_USD = 0.20  # tổng chi phí dự kiến (xấu nhất) vượt mức này thì dừng trước khi gọi (lần chạy v0.2)
CRAWL_REGION = "VN"  # vùng IP của máy crawl (đặc tả M1, quy tắc giá số 6); đặt tay, chưa đo
CRAWL_LOCALE = "en-US"  # locale mặc định của trình duyệt crawl; đặt tay, chưa đo
TEMPERATURE = 0.0
