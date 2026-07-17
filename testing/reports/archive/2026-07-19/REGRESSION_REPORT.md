# REGRESSION REPORT

## Trạng Thái
**PARTIAL PASS / BLOCKED E2E**

## Chi Tiết Backend (Local)
- Lệnh: `backend\venv\Scripts\pytest backend\tests -v`
- Trạng thái: **PASS**
- Số liệu: 143/143 tests passed.
- Log: Lỗi Prompt Injection và Crawler đã được fix. 

## Chi Tiết E2E / Frontend
- Trạng thái: **NOT TESTED (BLOCKED)**
- Lý do: Không thể chạy E2E Playwright và frontend test vì backend/database không thể được dựng lên (Docker Desktop chưa khởi động).

Không thể kết luận toàn bộ suite regression pass.
