# Hướng Hẫn Chạy Dự Án CyberSec Assistant

Tài liệu này hướng dẫn chi tiết cách cài đặt và vận hành hệ thống CyberSec Assistant nhanh nhất trên máy tính của bạn. Mọi cấu hình Database (Supabase Cloud) đã được thiết lập sẵn trong file cấu hình, bạn chỉ cần copy lệnh và chạy.

---

## 📌 Yêu Cầu Hệ Thống

*   **Chạy bằng Script (Khuyên dùng cho Windows):**
    *   **Python 3.10 hoặc 3.11** (Bắt buộc vì thư viện Rasa 3.6.20 chưa tương thích với Python 3.12+).
    *   Trình duyệt web (Chrome, Edge, Firefox...).
*   **Chạy bằng Docker:**
    *   Đã cài đặt **Docker** và **Docker Compose**.

---

## 🚀 Cách 1: Chạy Trực Tiếp Bằng File Script (Windows - Khuyên dùng)

Đây là cách nhanh nhất và nhẹ nhất để khởi chạy dự án trên hệ điều hành Windows.

### Bước 1: Huấn luyện chatbot Rasa (Chỉ cần chạy lần đầu hoặc khi đổi dữ liệu Rasa)
Mở terminal tại thư mục gốc của dự án và chạy file script train:
```powershell
.\train.bat
```
*(Script sẽ tự động tạo môi trường ảo Python venv cho Rasa, tải thư viện Rasa 3.6.20 và train model chatbot)*

### Bước 2: Khởi động hệ thống dịch vụ
Sau khi train xong, khởi chạy toàn bộ hệ thống bằng lệnh:
```powershell
.\start.bat
```
*(Script sẽ tự động kiểm tra môi trường, tạo venv cho backend, cài đặt dependencies, tắt các tiến trình trùng cổng và khởi động đồng thời Backend, Frontend, Rasa Server, Rasa Actions và Crawler)*

Sau khi khởi chạy thành công, trình duyệt sẽ tự động mở trang web dự án tại địa chỉ:
👉 **Frontend:** [http://localhost:8000](http://localhost:8000)

### Các script hỗ trợ quản lý khác:
*   **Xem trạng thái & Kiểm tra sức khỏe hệ thống:**
    ```powershell
    .\status.bat
    ```
*   **Tắt toàn bộ dịch vụ & Dọn dẹp cache:**
    ```powershell
    .\stop.bat
    ```

---

## 🐳 Cách 2: Khởi Chạy Bằng Docker Compose (Chạy được mọi hệ điều hành)

Nếu máy bạn đã cài sẵn Docker và không muốn cài đặt nhiều phiên bản Python cục bộ, bạn có thể chạy toàn bộ môi trường cô lập bằng Docker Compose.

### Bước 1: Khởi động tất cả dịch vụ trong Container
Mở terminal tại thư mục gốc của dự án và chạy:
```bash
docker-compose up --build -d
```

### Bước 2: Truy cập dịch vụ
Khi các container báo `Running` hoặc `Healthy`, truy cập tại các cổng:
*   **Giao diện người dùng (Frontend Web):** [http://localhost:3000](http://localhost:3000)
*   **Cổng API Backend FastAPI:** [http://localhost:8000](http://localhost:8000)
*   **Quản lý Redis Cache:** [http://localhost:8081](http://localhost:8081)
*   **Hệ thống Dashboard giám sát Grafana:** [http://localhost:3001](http://localhost:3001) (Tài khoản mặc định: `admin` / `admin`)
*   **Bộ giám sát chỉ số Prometheus:** [http://localhost:9090](http://localhost:9090)

### Bước 3: Dừng hệ thống Docker
```bash
docker-compose down
```

---

## 🔑 Tài Khoản Đăng Nhập Mặc Định

Để đăng nhập vào giao diện web (màn hình login), bạn sử dụng tài khoản Admin mặc định đã được seed sẵn trong database:

*   **Tên đăng nhập (Username):** `admin`
*   **Mật khẩu (Password):** `A1a!Y5Sorgv5xZ_Dr1JPQKjtunVKLVrBFAWA`
*   **Email liên kết:** `admin@cybersec.local`
*   **Vai trò (Role):** `admin`

### 📍 Địa chỉ đăng nhập (theo cách chạy)

*   **Chạy bằng Script (Windows):** [http://localhost:8000](http://localhost:8000)
*   **Chạy bằng Docker Compose:** [http://localhost:3000](http://localhost:3000)

### 🧾 Cách đăng nhập

*   Bạn có thể đăng nhập bằng **Username** (`admin`) **HOẶC Email** (`admin@cybersec.local`) kèm mật khẩu `A1a!Y5Sorgv5xZ_Dr1JPQKjtunVKLVrBFAWA`.
*   Mật khẩu mới được sinh ngẫu nhiên, dài và có **chữ hoa + chữ thường + số** nhằm đảm bảo an toàn khi đăng nhập.

### 👤 Quyền hạn của vai trò `admin`

Tài khoản này có quyền quản trị cao nhất, bao gồm: truy cập toàn bộ **Dashboard quản trị**, **quản lý người dùng**, **xem dữ liệu Crawler**, cấu hình hệ thống và truy cập các tính năng nội bộ của CyberSec Assistant.

### ⚠️ Phân biệt với tài khoản Grafana (tránh nhầm lẫn)

> Tại [http://localhost:3001](http://localhost:3001) có một tài khoản `admin` / `admin` — đây là tài khoản của **Grafana Dashboard giám sát** (xem ở mục Docker), **không phải** tài khoản đăng nhập web app CyberSec Assistant. Đừng dùng nhầm.

### 🔐 Lưu ý bảo mật

*   Đây là mật khẩu **mặc định seed sẵn** chỉ dành cho môi trường phát triển (development).
*   Nếu đưa dự án lên **production**, hãy **đổi mật khẩu** ngay sau lần đăng nhập đầu tiên và không sử dụng các thông tin mặc định này.

---

## ⚙️ Cấu Hình Database & Khóa API (Tùy chọn)

Dự án đã được cấu hình sẵn kết nối cloud Supabase dùng chung. Nếu bạn muốn cấu hình riêng:

1.  **Dùng Database cá nhân:**
    *   Tạo một project mới trên [Supabase Cloud](https://supabase.com).
    *   Truy cập SQL Editor trên Supabase, copy toàn bộ nội dung file [supabase_migration.sql](file:///d:/%C4%90%E1%BB%93%20%C3%A1n%20CNPM/backend/supabase_migration.sql) dán vào và chạy (Run) để khởi tạo cấu trúc bảng dữ liệu.
    *   Cập nhật các biến môi trường `SUPABASE_URL`, `SUPABASE_KEY` và `SUPABASE_SERVICE_ROLE_KEY` trong file `.env` và `.env.local` thành khóa dự án của bạn.
2.  **Khóa AI (Gemini) & Dịch vụ quét virus (VirusTotal):**
    *   Mở file `.env` (cho Docker) hoặc `.env.local` (cho chạy script) và nhập API Key của bạn tại các dòng:
        ```env
        GOOGLE_API_KEY=your_gemini_api_key
        VIRUSTOTAL_API_KEY=your_virustotal_api_key
        ```
