# BUG REPORT

- **Bug 01 (Fixed)**: Cơ chế `super_admin` cấp quyền lỏng lẻo thông qua username trong validator Pydantic. Đã bị loại bỏ và thay bằng Server-Side `SUPER_ADMIN_IDS` thông qua UUID.
- **Bug 02 (Fixed)**: Encoding lỗi khi chạy script 8h test (subprocess.run) trên Windows. Đã fix bằng `encoding="utf-8"`.
- Hiện tại không còn lỗi Critical hoặc High nào tồn đọng.
