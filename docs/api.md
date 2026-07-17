# 🔌 Đặc Tả API (API Documentation)

Hệ thống Backend FastAPI cung cấp một tập hợp các REST API và WebSockets endpoint để phục vụ cho Frontend và các dịch vụ khác. Tài liệu này mô tả chi tiết các nhóm API chính, các tham số đầu vào/đầu ra và cơ chế xác thực.

---

## 🔑 Cơ Chế Xác Thực (Authentication)

Dự án sử dụng xác thực dạng **JSON Web Token (JWT)**.
- **Header bắt buộc**: `Authorization: Bearer <access_token>`
- Token chứa thông tin `user_id`, `role`, và thời gian hết hạn (`exp`).
- Các endpoint admin yêu cầu role là `admin` hoặc `security_analyst`.

---

## 1. Nhóm API Xác Thực (`/api/auth`)

Quản lý đăng ký, đăng nhập, xác thực phiên làm việc.

### 1.1. Đăng nhập (Login)
- **Endpoint**: `POST /api/auth/login`
- **Body**:
  ```json
  {
    "username": "admin",
    "password": "<set-via-env-or-secret-store>"
  }
  ```
- **Phản hồi thành công (200 OK)**:
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "user": {
      "id": "a98a00b6-12c4-42b9-aa92-7fca7c90cfdf",
      "email": "admin@cybersec.local",
      "username": "admin",
      "role": "admin",
      "full_name": "System Administrator"
    }
  }
  ```

### 1.2. Đăng ký tài khoản (Register)
- **Endpoint**: `POST /api/auth/register`
- **Body**:
  ```json
  {
    "email": "user@cybersec.local",
    "username": "user123",
    "password": "StrongPassword123!",
    "full_name": "Normal User"
  }
  ```
- **Phản hồi thành công (201 Created)**:
  ```json
  {
    "status": "success",
    "message": "User registered successfully",
    "user_id": "b328bc12-4211-4ca3-bfa2-3c819bc298aa"
  }
  ```

---

## 2. Nhóm API Chatbot & Trợ Lý AI (`/api/chatbot`)

Xử lý luồng chat hybrid giữa Rasa và Gemini.

### 2.1. Gửi tin nhắn đến Chatbot
- **Endpoint**: `POST /api/chatbot/message`
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "message": "Lỗ hổng Log4Shell hoạt động như thế nào?",
    "session_id": "chat-session-xyz"
  }
  ```
- **Phản hồi thành công (200 OK)**:
  ```json
  {
    "response": "Lỗ hổng Log4Shell (CVE-2021-44228) là một lỗ hổng thực thi mã từ xa (RCE)...",
    "intent": "cve_explanation",
    "confidence": 0.98,
    "source": "gemini_rag",
    "suggested_actions": [
      "Xem cách khắc phục Log4Shell",
      "Quét kiểm tra hệ thống của tôi"
    ]
  }
  ```

### 2.2. Lấy lịch sử chat
- **Endpoint**: `GET /api/chatbot/history/{session_id}`
- **Headers**: `Authorization: Bearer <access_token>`
- **Phản hồi thành công (200 OK)**:
  ```json
  [
    {
      "sender": "user",
      "text": "Lỗ hổng Log4Shell hoạt động như thế nào?",
      "timestamp": "2026-07-14T22:34:00Z"
    },
    {
      "sender": "bot",
      "text": "Lỗ hổng Log4Shell (CVE-2021-44228)...",
      "timestamp": "2026-07-14T22:34:02Z"
    }
  ]
  ```

---

## 3. Nhóm API Tra Cứu CVE (`/api/cve`)

Tra cứu chi tiết lỗ hổng từ NVD (National Vulnerability Database) và dịch thông tin tự động.

### 3.1. Tìm kiếm thông tin CVE
- **Endpoint**: `GET /api/cve/{cve_id}`
- **Query Params**: `translate=true` (dịch sang tiếng Việt)
- **Phản hồi thành công (200 OK)**:
  ```json
  {
    "cve_id": "CVE-2021-44228",
    "description": "Apache Log4j2 JNDI features do not protect against attacker controlled LDAP...",
    "vietnamese_description": "Các tính năng JNDI của Apache Log4j2 không bảo vệ chống lại các máy chủ LDAP do kẻ tấn công kiểm soát...",
    "cvss_score": 10.0,
    "severity": "CRITICAL",
    "published_date": "2021-12-10",
    "remediation": "Cập nhật Apache Log4j lên phiên bản 2.15.0 trở lên hoặc thiết lập log4j2.formatMsgNoLookups=true"
  }
  ```

---

## 4. Nhóm API Quét An Toàn URL (`/api/url-check`)

Phân tích mã độc và nguy cơ lừa đảo (phishing) của đường dẫn.

### 4.1. Quét liên kết URL
- **Endpoint**: `POST /api/url-check/scan`
- **Headers**: `Authorization: Bearer <access_token>`
- **Body**:
  ```json
  {
    "url": "http://phishing-site-example.com/login"
  }
  ```
- **Phản hồi thành công (200 OK)**:
  ```json
  {
    "url": "http://phishing-site-example.com/login",
    "is_malicious": true,
    "phishing_heuristics_score": 85.0,
    "virustotal_stats": {
      "malicious": 12,
      "suspicious": 2,
      "harmless": 68,
      "undetected": 5
    },
    "risk_level": "HIGH",
    "details": "Domain sử dụng ký tự giả mạo thương hiệu và có 12 cảnh báo độc hại từ VirusTotal."
  }
  ```

---

## 5. Nhóm API Quản Trị Hệ Thống (`/api/v1/admin`)

*Nhóm API này yêu cầu quyền `admin`.*

### 5.1. Kích hoạt Crawler tin tức thủ công
- **Endpoint**: `POST /api/v1/admin/crawler/trigger`
- **Body**:
  ```json
  {
    "source": "threatpost"
  }
  ```
- **Phản hồi (200 OK)**:
  ```json
  {
    "status": "triggered",
    "message": "Crawler thread started successfully for source: threatpost"
  }
  ```

### 5.2. Quản lý mô hình Rasa NLU
- **Endpoint**: `POST /api/v1/admin/nlu/retrain`
- **Phản hồi (200 OK)**:
  ```json
  {
    "status": "training_started",
    "job_id": "nlu-train-8812"
  }
  ```

### 5.3. Xem danh sách ý định nhận diện thất bại (Failed Queries)
- **Endpoint**: `GET /api/v1/admin/nlu/failed-queries`
- **Phản hồi (200 OK)**:
  ```json
  [
    {
      "id": 41,
      "user_query": "làm sao để cấu hình ssl cho nginx?",
      "predicted_intent": "fallback",
      "confidence": 0.32,
      "created_at": "2026-07-14T20:12:00Z"
    }
  ]
  ```
- **Hành động**: Admin có thể gán nhãn lại các query này và đưa vào tập dữ liệu huấn luyện thông qua `POST /api/v1/admin/nlu/add-to-training`.
