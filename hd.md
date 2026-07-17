# Huong Dan Chay CyberSec Assistant

File nay de ban copy lenh va chay truc tiep tren Windows PowerShell.

## 1. Chay nhanh tren Windows

Copy nguyen khoi nay vao PowerShell:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\start.bat
```

Script `start.bat` se tu xu ly loi Docker Compose voi duong dan tieng Viet bang cach dong bo source sang `D:\codex_docker_cybersec_ascii`, roi chay Docker Compose tu duong dan ASCII do.

Neu may ban khong mo duoc duong dan co dau, dung ban ASCII mirror:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose up -d --build
```

## 2. Neu chay lan dau va bi bao thieu Rasa model

Neu thay loi:

```text
[ERROR] No Rasa model found in rasa\models.
```

copy chay 2 lenh nay:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\train.bat
.\scripts\windows\start.bat
```

## 3. Mo ung dung

Sau khi start thanh cong, mo:

```text
http://localhost:3000/login.html
```

Backend API:

```text
http://localhost:8000/docs
```

Health check:

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8000/health
Invoke-WebRequest -UseBasicParsing http://localhost:8002/health
Invoke-WebRequest -UseBasicParsing http://localhost:15005/
Invoke-WebRequest -UseBasicParsing http://localhost:15055/health
```

Neu cac lenh tren tra ve `200` hoac noi dung `healthy` la he thong dang chay. Rasa trong container van dung cong noi bo `5005` va Rasa Actions van dung cong noi bo `5055`, nhung tren Windows host du an dung `15005` va `15055` de tranh dai cong bi Windows reserve.

## 4. Dang nhap admin development

Trang dang nhap:

```text
http://localhost:3000/login.html
```

Tai khoan:

```text
Username: admin
Email: admin@cybersec.local
Password: xem trong file backend\ADMIN_CREDENTIALS.txt
```

Mo file credential bang lenh:

```powershell
notepad .\backend\ADMIN_CREDENTIALS.txt
```

Khong commit file nay len Git vi no chua mat khau local.

## 5. Kiem tra Docker dang chay

```powershell
docker ps
```

Neu chi muon xem cac container cua du an:

```powershell
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | Select-String "cybersec|codex_docker"
```

## 6. Dung he thong

Tu thu muc du an goc:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\stop.bat
```

Neu dang o mirror ASCII:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose down
```

## 7. Chay Docker Compose truc tiep

Khong nen chay lenh nay trong `D:\Đồ án CNPM`:

```powershell
docker compose up -d --build
```

Vi Docker Compose co the loi:

```text
x-docker-expose-session-sharedkey contains value with non-printable ASCII characters
```

Neu Docker bao loi bind cong `5005` hoac `5055`, do la vi Windows co the reserve cac dai cong quanh `4937-5036` va `5045-5144`. File `docker-compose.yml` hien da map Rasa ra host `15005` va Rasa Actions ra host `15055`, nen hay dung `.\scripts\windows\start.bat` hoac mirror ASCII da dong bo.

Neu muon chay Docker Compose truc tiep, copy chay:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose up -d --build
```

Neu can cap nhat mirror ASCII tu source goc truoc khi chay Docker Compose truc tiep, dung:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\start.bat
```

## 8. QA stack rieng

QA dung port rieng:

```text
Frontend QA: http://localhost:3100/login.html
Backend QA:  http://localhost:8100
Postgres QA: localhost:55432
```

Tai khoan QA admin:

```text
Username: qa_admin
Email: qa-admin@example.test
Password: dat bang bien moi truong QA_ADMIN_PASSWORD
```

Reset QA admin an toan:

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

Sau do dang nhap QA tai:

```text
http://localhost:3100/login.html
```

Dung username `qa_admin` va password trong bien `$qaPass` cua PowerShell hien tai.

## 9. Lenh sua loi nhanh

Restart backend/frontend:

```powershell
cd "D:\codex_docker_cybersec_ascii"
docker compose restart backend frontend
```

Build lai va chay lai:

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

## 10. Tom tat lenh can copy nhat

Lan dau:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\train.bat
.\scripts\windows\start.bat
```

Nhung lan sau:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\start.bat
```

Mo login:

```text
http://localhost:3000/login.html
```

Dung he thong:

```powershell
cd "D:\Đồ án CNPM"
.\scripts\windows\stop.bat
```
