# 📌 Quy Định Phiên Bản (Project Versioning)

Dự án CyberSec Assistant áp dụng các nguyên tắc chuẩn mực trong ngành công nghiệp phần mềm để quản lý phiên bản và lịch sử thay đổi của mã nguồn. Điều này giúp các lập trình viên và nhà tuyển dụng đánh giá được tính kỷ luật và quy trình phát hành sản phẩm chuyên nghiệp.

---

## 1. Chuẩn Semantic Versioning (SemVer)

Phiên bản của hệ thống được định nghĩa theo định dạng ba con số: **MAJOR.MINOR.PATCH** (Ví dụ: `1.2.0`).

- **MAJOR (Số lớn)**: Tăng khi có những thay đổi lớn về mặt kiến trúc, không tương thích ngược (API breaking changes).
  - *Ví dụ*: Chuyển đổi toàn bộ cơ chế DB cục bộ sang Supabase Cloud, thay thế hoàn toàn Rasa bằng một Framework chatbot khác.
- **MINOR (Số vừa)**: Tăng khi thêm các tính năng mới lớn nhưng vẫn đảm bảo tương thích ngược (backward-compatible features).
  - *Ví dụ*: Thêm trang quét mã độc URL, tích hợp Grafana monitoring, thêm crawler nguồn tin mới.
- **PATCH (Số nhỏ)**: Tăng khi sửa lỗi phần mềm, cải thiện hiệu năng hoặc cập nhật tài liệu mà không thêm tính năng mới (bug fixes & minor adjustments).
  - *Ví dụ*: Fix lỗi gán nhãn trong migrations, sửa đổi đường dẫn file start.bat, thêm docstrings cho code.

---

## 2. Quy Tắc Gán Nhãn Phiên Bản (Git Tagging)

Mỗi lần phát hành một phiên bản ổn định (Release), lập trình viên bắt buộc phải tạo một Git Tag tương ứng trên nhánh `main`:

### Cách tạo và đẩy Tag lên GitHub:
1. **Kiểm tra phiên bản hiện tại và tạo Tag**:
   ```bash
   git tag -a v1.0.0 -m "Release version 1.0.0 - First stable release with Docker Compose and Supabase integration"
   ```
2. **Đẩy Tag lên Remote Repository**:
   ```bash
   git push origin v1.0.0
   ```

---

## 3. Lịch Trình Phát Hành (Release Roadmap)

Hệ thống đang được phát triển theo các cột mốc phiên bản sau:

### 🚀 v1.0.0 (Phiên bản Hiện tại)
- Thiết lập thành công hạ tầng chạy Docker Compose.
- Tích hợp Rasa Chatbot và Gemini LLM (RAG).
- Hỗ trợ chức năng dịch và tra cứu CVE.
- Tích hợp kết nối cơ sở dữ liệu Supabase Cloud.
- Hệ thống giám sát cơ bản Prometheus & Grafana.

### 📅 v1.1.0 (Dự kiến)
- Tích hợp cơ chế quét tệp tin độc hại (File Scanner) trực tiếp trên giao diện web.
- Tối ưu hóa bộ nhớ đệm ChromaDB để tăng tốc tìm kiếm RAG.
- Bổ sung trang quản lý quyền người dùng nâng cao (RBAC - Role-Based Access Control) trên Frontend.

### 📅 v2.0.0 (Dự kiến)
- Chuyển đổi kiến trúc sang Kubernetes (K8s) cho các môi trường sản xuất lớn.
- Hỗ trợ đa ngôn ngữ hoàn toàn (Bilingual Chatbot: Tiếng Anh và Tiếng Việt).
