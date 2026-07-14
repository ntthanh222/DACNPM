# 🤝 Hướng Dẫn Đóng Góp (Contributing Guidelines)

Chúng tôi rất hoan nghênh và đánh giá cao mọi sự đóng góp từ cộng đồng và các thành viên để dự án **CyberSec Assistant** ngày càng hoàn thiện hơn. Để đảm bảo chất lượng mã nguồn và sự thống nhất trong quy trình làm việc, vui lòng tuân thủ các hướng dẫn dưới đây.

---

## 1. Quy Quy Định Nhánh (Branching Strategy)

Dự án sử dụng mô hình Git Branching đơn giản. Khi muốn phát triển một tính năng mới hoặc sửa lỗi, hãy tạo một nhánh mới từ nhánh `main`:

- Nhánh tính năng mới: `feature/ten-tinh-nang` (Ví dụ: `feature/url-scanner-ui`)
- Nhánh sửa lỗi: `bugfix/ten-loi` (Ví dụ: `bugfix/auth-session-leak`)
- Nhánh cải tiến tài liệu: `docs/ten-tai-lieu` (Ví dụ: `docs/api-specs`)

---

## 2. Quy Chuẩn Đặt Tên Commit (Commit Message Standards)

Chúng tôi khuyến khích sử dụng chuẩn **Conventional Commits** để tự động hóa việc theo dõi lịch sử thay đổi:

Định dạng chung: `<type>: <description>`

### Các loại Type phổ biến:
- `feat`: Khi thêm một tính năng mới (Ví dụ: `feat: add VirusTotal integration for URL scanner`).
- `fix`: Khi sửa một lỗi trong mã nguồn (Ví dụ: `fix: resolve user login redirect issue`).
- `docs`: Khi cập nhật tài liệu hướng dẫn hoặc bổ sung chú thích code (Ví dụ: `docs: update setup steps in hd.md`).
- `style`: Thay đổi không ảnh hưởng đến logic code (CSS, định dạng code, dấu cách, v.v.).
- `refactor`: Tái cấu trúc mã nguồn để sạch hơn mà không đổi hành vi.
- `test`: Thêm hoặc sửa các bộ kiểm thử unit tests (Ví dụ: `test: add auth-service unit tests`).

---

## 3. Quy Trình Phát Triển & Gửi Pull Request (PR Workflow)

1. **Fork** repository này về tài khoản GitHub cá nhân của bạn.
2. **Clone** bản fork về máy tính local:
   ```bash
   git clone https://github.com/your-username/DACNPM.git
   ```
3. Tạo nhánh mới để bắt đầu lập trình (đảm bảo xuất phát từ `main` mới nhất):
   ```bash
   git checkout -b feature/AmazingFeature
   ```
4. Thực hiện các chỉnh sửa, lập trình tính năng mới.
5. **Chạy kiểm thử cục bộ** trước khi commit để đảm bảo không làm gãy hệ thống:
   - Truy cập thư mục frontend và chạy:
     ```bash
     cd frontend && npm test
     ```
6. Commit các thay đổi với thông điệp rõ ràng:
   ```bash
   git commit -m "feat: add secure session route guard to admin page"
   ```
7. Đẩy nhánh của bạn lên bản Fork trên GitHub:
   ```bash
   git push origin feature/AmazingFeature
   ```
8. Mở Pull Request (PR) từ nhánh của bạn đến nhánh `main` của repository gốc và mô tả chi tiết các thay đổi của bạn để được review.

Cảm ơn sự đóng góp của bạn!
