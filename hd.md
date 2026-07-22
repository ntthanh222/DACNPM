# Hướng Dẫn Chạy CyberSec Assistant

Tài liệu này dành cho Windows PowerShell. Dự án đang nằm ở:

```text
D:\Đồ án CNPM
```

Do Docker Desktop trên Windows có thể lỗi với đường dẫn có ký tự tiếng Việt, dự án dùng script để đồng bộ sang thư mục ASCII:

```text
D:\codex_docker_cybersec_ascii
```

## 1. Chạy Project Bằng Docker

Mở PowerShell, chạy:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\start.bat
```

Script này sẽ:

- đồng bộ source sang `D:\codex_docker_cybersec_ascii`;
- build lại Docker image khi cần;
- chạy Docker Compose từ thư mục ASCII;
- tránh lỗi `x-docker-expose-session-sharedkey contains value with non-printable ASCII characters`.

Nếu muốn chạy Docker Compose trực tiếp, dùng thư mục mirror:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose up -d --build
```

Không nên chạy trực tiếp `docker compose up -d --build` trong `D:\Đồ án CNPM` nếu Docker Desktop còn lỗi với đường dẫn tiếng Việt.

## 2. Chạy Lần Đầu Nếu Thiếu Rasa Model

Nếu Docker báo lỗi thiếu Rasa model:

```text
[ERROR] No Rasa model found in /app/models
```

chạy:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\train.bat
.\scripts\windows\start.bat
```

## 3. Mở Ứng Dụng

Frontend:

```text
http://localhost:3000/login.html
```

Backend API docs:

```text
http://localhost:8000/docs
```

Các service chính:

```text
Frontend:      http://localhost:3000
Backend:       http://localhost:8000
Crawler:       http://localhost:8002
Rasa:          http://localhost:15005
Rasa Actions:  http://localhost:15055
Prometheus:    http://localhost:9090
Grafana:       http://localhost:3001
```

Lưu ý: trong container, Rasa vẫn dùng port nội bộ `5005` và Rasa Actions dùng port nội bộ `5055`. Trên Windows host, dự án map ra `15005` và `15055` để tránh dải port bị Windows reserve.

## 4. Tài Khoản Admin Development

Trang đăng nhập:

```text
http://localhost:3000/login.html
```

Tài khoản admin local/development:

```text
Username: admin
Email: admin@cybersec.local
Password: [REDACTED_DEV_ADMIN_PASSWORD] (Hoặc sử dụng biến môi trường E2E_ADMIN_PASSWORD)
```

Mật khẩu trên chỉ dùng cho local/dev. Không dùng credential này cho production hoặc môi trường public.

File credential local cũng đã được đồng bộ tại:

```powershell
cd "D:\Đồ án CNPM"
notepad .\backend\ADMIN_CREDENTIALS.txt
```

File `backend\ADMIN_CREDENTIALS.txt` là file local đã được `.gitignore`. Không commit file này lên Git.

Bạn có thể đăng nhập bằng `admin` hoặc `admin@cybersec.local`.

## 5. Tài Khoản Grafana

Grafana dùng để xem monitoring:

```text
http://localhost:3001
```

Tài khoản mặc định theo `docker-compose.yml`:

```text
Username: admin
Password: admin
```

Chỉ dùng tài khoản này cho môi trường local/dev.

## 6. Kiểm Tra Docker Đang Chạy

Xem container:

```powershell
docker ps
```

Xem riêng các container của dự án:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "cybersec|codex_docker"
```

Chạy script kiểm tra trạng thái:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\status.bat
```

Health check thủ công:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8002/health
Invoke-WebRequest -UseBasicParsing http://localhost:15005/
Invoke-WebRequest -UseBasicParsing http://localhost:15055/health
Invoke-WebRequest -UseBasicParsing http://localhost:9090/-/ready
```

Nếu các lệnh trả về `200`, `healthy`, hoặc nội dung OK tương đương thì stack đang chạy.

## 7. Dừng Project

Từ thư mục gốc:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\stop.bat
```

Hoặc nếu đang ở mirror ASCII:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose down
```

## 8. Restart Và Xem Log

Restart backend/frontend:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose restart backend frontend
```

Build lại toàn bộ:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\start.bat
```

Xem log backend:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose logs -f backend
```

Xem log frontend:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose logs -f frontend
```

Xem log Rasa:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose logs -f rasa
```

## 9. Chạy Test Nhanh

Frontend unit/regression:

```powershell
cd "D:\Đồ án CNPM\frontend"
npm test
```

Backend tests trong Docker:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker exec codex_docker_cybersec_ascii-backend-1 pytest backend/tests -q
```

Regression slice nhanh:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker exec codex_docker_cybersec_ascii-backend-1 pytest backend/tests/test_system_regressions.py backend/tests/test_local_connection.py -q
```

Script verify tổng hợp:

```powershell
cd "D:\Đồ án CNPM"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\verify-project.ps1
```

## 10. QA Stack Riêng

QA dùng port riêng để tránh đụng development:

```text
Frontend QA: http://localhost:3100/login.html
Backend QA:  http://localhost:8100
Postgres QA: localhost:55432
Redis QA:    localhost:6380
```

Chạy QA stack:

```powershell
cd "D:\Đồ án CNPM"
docker compose -f docker-compose.test.yml up -d --build
```

Tài khoản QA admin:

```text
Username: qa_admin
Email: qa-admin@example.test
Password: đặt bằng biến môi trường QA_ADMIN_PASSWORD
```

Ví dụ reset QA admin an toàn:

```powershell
cd "D:\Đồ án CNPM"
$qaPass = 'Qa-' + ([guid]::NewGuid().ToString('N')) + '!9a'
$env:ENVIRONMENT='test'
$env:APP_ENV='test'
$env:ALLOW_QA_MUTATIONS='true'
$env:QA_DATABASE_CONFIRMATION='ISOLATED_QA_DATABASE'
$env:SUPABASE_URL='http://local-qa.invalid'
$env:DB_HOST='localhost'
$env:DB_PORT='55432'
$env:DB_NAME='cybersec_qa'
$env:DB_USER='postgres'
$env:DB_PASSWORD='postgres'
$env:QA_POSTGRES_CONTAINER='cybersec-postgres-qa'
$env:API_BASE_URL='http://localhost:8100'
$env:QA_ADMIN_PASSWORD=$qaPass
.\backend\venv\Scripts\python.exe testing\scripts\reset_qa_admin.py
.\backend\venv\Scripts\python.exe testing\scripts\qa_admin_login_check.py
```

Sau đó đăng nhập QA tại:

```text
http://localhost:3100/login.html
```

Dùng username `qa_admin` và password đang nằm trong biến `$qaPass` của PowerShell hiện tại.

## 11. Dọn Docker An Toàn

Xem dung lượng Docker:

```powershell
docker system df
```

Phân tích cleanup an toàn, không xóa dữ liệu:

```powershell
cd "D:\Đồ án CNPM"
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\windows\cleanup-safe.ps1
```

Dọn build cache Docker an toàn hơn `docker system prune -a`:

```powershell
docker builder prune -f
```

Không xóa volume nếu chưa biết volume đó chứa dữ liệu gì.

## 12. Lỗi Thường Gặp

### Lỗi non-printable ASCII khi Docker Compose

Lỗi:

```text
x-docker-expose-session-sharedkey contains value with non-printable ASCII characters
```

Cách xử lý:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\start.bat
```

Script sẽ chạy Docker Compose từ `D:\codex_docker_cybersec_ascii`.

### Lỗi bind port 5005 hoặc 5055

Windows có thể reserve các dải port quanh `4937-5036` và `5045-5144`. Dự án đã map:

```text
Rasa host port:         15005 -> container 5005
Rasa Actions host port: 15055 -> container 5055
```

Hãy dùng URL `http://localhost:15005` và `http://localhost:15055`.

### Đăng nhập admin thất bại

Kiểm tra theo thứ tự:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\status.bat
notepad .\backend\ADMIN_CREDENTIALS.txt
```

Sau đó thử lại:

```text
Username: admin
Email: admin@cybersec.local
Password: [REDACTED_DEV_ADMIN_PASSWORD] (Hoặc sử dụng biến môi trường E2E_ADMIN_PASSWORD)
```

Nếu vẫn lỗi, xem log backend:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose logs --tail=100 backend
```

## 13. Tóm Tắt Lệnh Hay Dùng

Chạy project:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\start.bat
```

Mở app:

```text
http://localhost:3000/login.html
```

Xem mật khẩu admin app:

```powershell
cd "D:\Đồ án CNPM"
notepad .\backend\ADMIN_CREDENTIALS.txt
```

Kiểm tra trạng thái:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\status.bat
```

Dừng project:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\stop.bat
```
