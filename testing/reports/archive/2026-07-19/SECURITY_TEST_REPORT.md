# SECURITY TEST REPORT

## Trạng Thái
**PARTIAL PASS / BLOCKED LIVE TEST**

## Chi Tiết Backend (Local)
- Lệnh: `backend\venv\Scripts\pytest backend\tests -v -m "security"`
- Trạng thái: **PASS**
- Các vấn đề đã sửa:
  - Lỗi Prompt Injection (`test_prompt_injection.py`) đã được phân tách thành Unit Test (Mocked) và Integration Test (Live). Cả hai đều không còn nuốt lỗi và verify đúng cơ chế chặn mã độc (Confidence score).
  - Lỗi Dependency path (`test_chat_stream_security.py`) đã được sửa bằng `Path(__file__)`.

## Chi Tiết Penetration / Live API (NVD, VirusTotal)
- Trạng thái: **NOT TESTED (BLOCKED)**
- Lý do: Môi trường Docker Desktop bị down, không thể khởi tạo backend server và frontend đầy đủ cho các kịch bản Live API Security.

Không giữ các tuyên bố cứng nhắc về bảo mật khi chưa thể test E2E.
