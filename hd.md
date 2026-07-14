# Hướng Dẫn Chạy Dự Án CyberSec Assistant

Tài liệu này hướng dẫn chi tiết cách cài đặt và vận hành hệ thống CyberSec Assistant nhanh nhất trên máy tính của bạn thông qua Docker. Mọi cấu hình đã được tối ưu hóa để khởi chạy bằng Docker Compose.

---

## 📌 Yêu Cầu Hệ Thống

Để khởi chạy dự án, máy tính của bạn cần được cài đặt sẵn:
1. **Docker Desktop** (hoặc Docker Engine & Docker Compose).
2. **Git** (để quản lý mã nguồn).

---

## 🚀 Cách 1: Sử Dụng File Script Tiện Ích (Windows - Khuyên dùng)

Các script tiện ích được thiết kế để tự động hóa toàn bộ thao tác khởi chạy trên hệ điều hành Windows.

### Bước 1: Huấn luyện chatbot Rasa (Chỉ chạy lần đầu hoặc khi đổi dữ liệu Rasa)
Mở terminal tại thư mục gốc của dự án và chạy file script train:
```powershell
.\scripts\windows\train.bat
```
*(Script này sẽ tự động khởi chạy container Rasa để train model chatbot, sau đó lưu model được sinh ra vào thư mục `rasa/models/`)*

### Bước 2: Khởi động hệ thống dịch vụ
Sau khi quá trình huấn luyện kết thúc, chạy lệnh sau để khởi động toàn bộ dịch vụ:
```powershell
.\scripts\windows\start.bat
```
*(Script sẽ tự động build, khởi chạy các container Docker cần thiết, kiểm tra sức khỏe của dịch vụ và tự động mở giao diện Frontend trên trình duyệt)*

Sau khi khởi chạy thành công, trình duyệt sẽ tự động mở trang web dự án tại địa chỉ:
👉 **Frontend Web:** [http://localhost:3000](http://localhost:3000)

### Các script quản lý khác trên Windows:
*   **Kiểm tra trạng thái & sức khỏe hệ thống:**
    ```powershell
    .\scripts\windows\status.bat
    ```
*   **Tắt toàn bộ dịch vụ:**
    ```powershell
    .\scripts\windows\stop.bat
    ```

---

## 🐳 Cách 2: Khởi Chạy Bằng Lệnh Docker Compose Trực Tiếp (Mọi Hệ Điều Hành)

Nếu bạn sử dụng Linux/macOS hoặc muốn chạy trực tiếp bằng dòng lệnh của Docker Compose:

### Bước 1: Huấn luyện chatbot Rasa
Mở terminal tại thư mục gốc của dự án và chạy lệnh sau:
```bash
docker compose run --rm --no-deps --entrypoint rasa rasa train --config /app/config.yml --domain /app/domain.yml --data /app/data --out /app/models
```

### Bước 2: Khởi động tất cả các container dịch vụ
Chạy lệnh sau để build và khởi động hệ thống dưới dạng tiến trình ngầm (detached mode):
```bash
docker compose up -d --build
```

### Bước 3: Kiểm tra và Truy cập dịch vụ
Truy cập các dịch vụ đang chạy qua các địa chỉ và cổng:
*   **Giao Diện Người Dùng (Frontend):** [http://localhost:3000](http://localhost:3000)
*   **Backend API (FastAPI):** [http://localhost:8000](http://localhost:8000)
*   **Trang API Health Check:** [http://localhost:8000/health](http://localhost:8000/health)
*   **Cổng API Crawler:** [http://localhost:8002](http://localhost:8002)
*   **Quản Lý Redis Cache (Redis Commander):** [http://localhost:8081](http://localhost:8081)
*   **Hệ thống Dashboard giám sát Grafana:** [http://localhost:3001](http://localhost:3001) (Tài khoản mặc định: `admin` / `admin`)
*   **Bộ thu thập chỉ số Prometheus:** [http://localhost:9090](http://localhost:9090)

### Bước 4: Dừng hệ thống Docker
```bash
docker compose down
```

---

## 🔑 Tài Khoản Đăng Nhập Mặc Định

Để đăng nhập vào hệ thống Web App CyberSec Assistant (qua trang login), sử dụng tài khoản Quản trị viên (Admin) mặc định đã được seed sẵn trong cơ sở dữ liệu:

*   **Tên đăng nhập (Username):** `admin`
*   **Email liên kết:** `admin@cybersec.local`
*   **Mật khẩu (Password):** `A1a!Y5Sorgv5xZ_Dr1JPQKjtunVKLVrBFAWA`
*   **Vai trò (Role):** `admin`

### 👤 Quyền hạn của tài khoản `admin`
Tài khoản admin này có quyền cao nhất để truy cập toàn bộ **Dashboard quản trị**, **quản lý người dùng**, **xem dữ liệu Crawler**, cấu hình hệ thống và giao tiếp với Rasa chatbot.

### ⚠️ Phân biệt với tài khoản Grafana
> **Lưu ý:** Giao diện Grafana tại [http://localhost:3001](http://localhost:3001) sử dụng tài khoản `admin` / `admin` để quản lý các chỉ số monitor, **không phải** tài khoản truy cập Web App chính.

---

## ⚙️ Cấu Hình Database & API Key (Tùy chọn)

Dự án đã được tích hợp sẵn cấu hình kết nối đám mây Supabase dùng chung. Để tùy chỉnh hoặc dùng API Key cá nhân của bạn:

1. **Cơ sở dữ liệu cá nhân (Supabase):**
   - Đăng ký và tạo project tại [Supabase Cloud](https://supabase.com).
   - Vào mục SQL Editor của project Supabase mới, sao chép nội dung file [001_core_schema.sql](file:///d:/Đồ%20án%20CNPM/backend/database/migrations/001_core_schema.sql) và [002_fix_users.sql](file:///d:/Đồ%20án%20CNPM/backend/database/migrations/002_fix_users.sql) rồi nhấn **Run** để khởi tạo các bảng dữ liệu cần thiết.
   - Cập nhật thông tin cấu hình `SUPABASE_URL`, `SUPABASE_KEY` và `SUPABASE_SERVICE_ROLE_KEY` trong các file môi trường `.env` hoặc `.env.local` ở thư mục gốc.

2. **Cấu hình Trợ lý AI (Gemini) & Dịch vụ quét (VirusTotal):**
   - Lấy API Key từ Google AI Studio và VirusTotal.
   - Điền thông tin API Key vào file cấu hình `.env` hoặc `.env.local`:
     ```env
     GEMINI_API_KEY=your_gemini_api_key
     VIRUSTOTAL_API_KEY=your_virustotal_api_key
     ```
