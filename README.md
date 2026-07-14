# DACNPM - CyberSec Assistant

Dự án phát triển trợ lý ảo hỗ trợ an toàn thông tin (CyberSec Assistant). Hệ thống tích hợp mô hình chatbot Rasa AI, cơ sở dữ liệu tri thức RAG (Retrieval-Augmented Generation) kết hợp với Gemini LLM để phản hồi các thắc mắc bảo mật, cập nhật tin tức an ninh mạng và phân tích các lỗ hổng CVE.

Vui lòng tham khảo [hd.md](hd.md) để biết thêm chi tiết về cài đặt và hướng dẫn vận hành hệ thống.

---

## 🛠️ Công Nghệ Sử Dụng

- **Frontend**: HTML5, Vanilla CSS, Vanilla JavaScript (MVC pattern, controllers & services).
- **Backend**: FastAPI (Python), REST API, Websockets.
- **AI Chatbot**: Rasa Open Source 3.6.20 (Custom Action Server).
- **LLM/RAG**: Google Gemini API, ChromaDB (Vector Database).
- **Cache**: Redis.
- **Monitoring**: Prometheus, Grafana.
- **Containerization**: Docker, Docker Compose.
