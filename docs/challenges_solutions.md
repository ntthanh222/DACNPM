# ⚡ Thách Thức và Giải Pháp Kỹ Thuật (Challenges & Solutions)

Trong quá trình phát triển và hoàn thiện dự án **CyberSec Assistant**, nhóm phát triển đã đối mặt với một số rào cản kỹ thuật quan trọng liên quan đến tính tương thích của thư viện AI, cơ sở dữ liệu cloud và tối ưu hiệu năng. Dưới đây là phân tích chi tiết về các thách thức và giải pháp kỹ thuật đã được áp dụng.

---

## 1. Tương Thích Rasa Open Source & Phiên Bản Python

### 🔴 Thách thức
- **Mô tả**: Rasa Open Source 3.6.20 sử dụng một số thư viện C-extensions cũ (như `uvloop`, `ruamel.yaml.clib`) vốn chưa tương thích hoặc bị lỗi biên dịch trên Python 3.12+ (phiên bản Python mặc định trên hệ điều hành của nhiều nhà phát triển hiện nay).
- **Hệ quả**: Việc cài đặt dependencies trực tiếp từ `pip install -r requirements.txt` trên Windows thường bị lỗi biên dịch Visual C++ Build Tools, đồng thời Rasa hoạt động kém ổn định do xung đột phiên bản thư viện con.

### 🟢 Giải pháp áp dụng
- **Docker hóa cô lập**: Nhóm đã chuyển toàn bộ môi trường chạy Rasa và Rasa Action Server sang chạy hoàn toàn bằng Docker.
- **Sử dụng Container chính thức**: Sử dụng image nền chính thức `rasa/rasa:3.6.20-full` chạy trên nền Python 3.10 ổn định. 
- **Thiết lập Volume Mount**: Thư mục `rasa/models`, `rasa/data`, `config.yml`, `domain.yml` được bind-mount trực tiếp từ máy local vào container, giúp quá trình huấn luyện bằng lệnh Docker vẫn lưu trữ model thành công ra bên ngoài:
  ```bash
  docker compose run --rm --no-deps --entrypoint rasa rasa train --config /app/config.yml --domain /app/domain.yml --data /app/data --out /app/models
  ```
- **Hệ quả**: Nhà phát triển không cần cài đặt bất kỳ môi trường Python local nào mà vẫn có thể chạy Rasa bình thường trên mọi hệ điều hành (Windows, Linux, macOS).

---

## 2. Quản Trị Schema Cơ Sở Dữ Liệu Trên Supabase Cloud

### 🔴 Thách thức
- **Mô tả**: Khi đưa database lên Cloud (Supabase), cú pháp SQL migrations ban đầu chạy trong SQL Editor dạng `INSERT INTO users` không chỉ định rõ schema. 
- **Lỗi phát sinh**: Mặc định, Supabase sẽ cố gắng chèn bản ghi vào schema auth nội bộ (`auth.users`), dẫn đến lỗi xung đột cú pháp vì bảng `auth.users` sử dụng tên cột là `encrypted_password` thay vì `password_hash` của bảng nghiệp vụ, gây ra lỗi nghiêm trọng `column password_hash does not exist`.

### 🟢 Giải pháp áp dụng
- **Chỉ định Schema tường minh**: Toàn bộ tệp migrations được cấu trúc lại và khai báo rõ ràng tiền tố `public.` cho bảng nghiệp vụ:
  ```sql
  INSERT INTO public.users (email, username, password_hash, role, ...)
  VALUES ('admin@cybersec.local', 'admin', '$2b$12$...', 'admin', ...)
  ```
- **Cơ chế Idempotent**: Thêm các ràng buộc kiểm tra `CREATE TABLE IF NOT EXISTS` và `ALTER TABLE public.users ADD COLUMN IF NOT EXISTS` giúp các tệp SQL migrations có thể chạy lại nhiều lần một cách an toàn mà không làm mất dữ liệu cũ.

---

## 3. Luồng Định Tuyến Chatbot Hybrid (Hybrid Intention Routing)

### 🔴 Thách thức
- **Mô tả**: Chatbot Rasa rất tốt trong việc nhận diện ý định có tính lặp lại (ví dụ chào hỏi, hỏi thông tin tài khoản, cấu hình cài đặt). Tuy nhiên, đối với các truy vấn bảo mật rộng và chuyên sâu (ví dụ: "Làm cách nào để cấu hình an toàn cho máy chủ Apache?"), Rasa không thể tự động trả lời chính xác nếu không huấn luyện tập ngữ liệu khổng lồ.
- **Hệ quả**: Chatbot phản hồi kém tự nhiên hoặc thường xuyên rơi vào trạng thái `out_of_scope` (fallback).

### 🟢 Giải pháp áp dụng
- **Xây dựng bộ định tuyến Hybrid**: 
  - Khi người dùng gửi câu hỏi, FastAPI chuyển tiếp đến Rasa NLU trước.
  - Nếu Rasa nhận diện ý định có độ tin cậy thấp (confidence < 0.7) hoặc nhận diện ý định là câu hỏi kỹ thuật bảo mật chuyên sâu (`ask_security_kb`), Rasa Custom Action Server hoặc Backend API sẽ tự động kích hoạt luồng xử lý RAG & Gemini.
  - LLM Gemini kết hợp với vector tìm kiếm từ ChromaDB sẽ trả lời câu hỏi dựa trên kho tài liệu kiến thức bảo mật nội bộ.
- **Kết quả**: chatbot phản hồi chính xác cả những câu hỏi cơ bản lẫn những thắc mắc kỹ thuật phức tạp với tỷ lệ fallback được tối ưu.

---

## 4. Giới Hạn Tốc Độ (Rate Limiting) & Quản Lý Caching

### 🔴 Thách thức
- **Mô tả**: Các API tìm kiếm CVE trực tiếp từ NVD API hoặc gọi quét URL bằng VirusTotal API có giới hạn số lượng request khắt khe đối với tài khoản miễn phí (Rate Limit). Nếu người dùng spam yêu cầu liên tục, hệ thống sẽ bị block và ngừng hoạt động.

### 🟢 Giải pháp áp dụng
- **Redis Caching**: Tích hợp Redis làm tầng cache lưu trữ tạm thời:
  - Kết quả tra cứu CVE được cache trong Redis với thời gian hết hạn (TTL) là 7 ngày. Khi có yêu cầu trùng mã CVE, hệ thống trả về ngay lập tức từ Redis mà không cần gọi API ngoài.
  - Kết quả quét mã độc URL được cache trong 24 giờ.
- **Circuit Breaker & Rate Limiting**: Thiết lập decorator giới hạn tần suất gọi API ở backend (`@limiter.limit("10/minute")`) để bảo vệ tài nguyên hệ thống và ngăn chặn tấn công từ chối dịch vụ (DoS).
