# Phiếu chấm nghe TTS tiếng Việt (P1-02b)

Người nghe tự chấm. **Không ai chấm thay**, kể cả người/agent chuẩn bị bộ clip.

## Chuẩn bị
1. Lấy `listening.zip` (hoặc thư mục `listening/`, xem README, mục "Bộ nghe"): các file `L01.wav`… và `scoring-sheet.csv`. Gói chia sẻ **không chứa đáp án**.
2. **Không mở `answer-key.json`** (nằm riêng ở thư mục cha, chỉ điều phối viên giữ) cho tới khi mọi người chấm xong. Tên clip là mã ngẫu nhiên để tránh thiên vị theo provider.
3. Mỗi người chấm riêng, dùng cùng loa/tai nghe. Nghe tối đa 2 lần mỗi clip.
4. Mỗi clip có câu gốc ở cột B (người nghe đọc câu này để biết giọng *phải* đọc gì).

## Thang điểm (1–5, số nguyên)
| Điểm | Tự nhiên | Đúng dấu/thanh | Đọc số | Đọc tên riêng |
|---|---|---|---|---|
| 5 | Như người thật đọc quảng cáo | Không nghe sai thanh | Đọc đúng hết, ngắt tự nhiên | Dễ hiểu, chấp nhận được với tên tiếng Anh |
| 4 | Hơi máy nhưng nghe thoải mái | Sai 1 thanh, vẫn hiểu | Đúng, hơi lạ chỗ ngắt | Hơi lệch nhưng nhận ra |
| 3 | Rõ là giọng máy, nghe được | Sai vài thanh, phải đoán | Đúng nhưng sai 1 chữ số/đơn vị nhỏ | Lệch rõ, vẫn đoán được |
| 2 | Khó chịu, ngắt sai nhịp | Sai nhiều, khó hiểu | Sai giá trị hoặc đơn vị | Không nhận ra tên |
| 1 | Không dùng được | Không hiểu được | Sai hẳn / bỏ qua số | Đọc sai hoàn toàn / bỏ qua |

- **Đọc số** chỉ chấm với clip có số (giá, %, đơn vị, ngày); clip khác để trống.
- **Đọc tên riêng** chỉ chấm với clip có tên (Lock&Lock, ElevenLabs, Pro, AI, Starter…); clip khác để trống.
- **Sai giá hoặc sai đơn vị là lỗi nghiêm trọng nhất** (cùng tinh thần ADR-0002: sai giá là lỗi nặng nhất). Nếu nghe sai giá trị: ghi "SAI GIÁ" ở cột ghi chú, và cho "đọc số" tối đa 2.
- Ghi chú thêm: giọng nam hay nữ, miền Bắc/Nam, nghe có méo, cụt chữ, lặp, rè không.

## Cách so sánh bản chuẩn hoá và bản gốc
Một số câu (giá, 1,2 triệu, ngày, thập phân) có 2 clip cho mỗi giọng: một clip qua `normalize_vi`, một clip đưa văn bản gốc. Hai clip này có
mã khác nhau; cứ chấm bình thường, sau đó đối chiếu bằng `answer-key.json`.

## Sau khi chấm
Mỗi người gửi `scoring-sheet.csv` đã điền. Điều phối viên tính trung bình theo `config` và `variant` từ `answer-key.json`
rồi điền vào bảng kết quả trong README và ADR-0004. Điểm là căn cứ để chốt "chính / dự phòng"; ngưỡng đề xuất ở ADR.
