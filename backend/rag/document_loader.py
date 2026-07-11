"""
Document loader for RAG knowledge base.

Loads and prepares documents from various sources:
- Security news articles
- Security tips and best practices
- CVE vulnerability data
- Incident response procedures
"""

from typing import List, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DocumentLoader:
    """Load and prepare documents for RAG knowledge base."""

    @staticmethod
    def load_from_news(articles: List[Dict]) -> List[Dict]:
        """
        Convert news articles to RAG documents.

        Args:
            articles: List of news article dicts from database

        Returns:
            List of document dicts for vector store
        """
        documents = []
        for i, article in enumerate(articles):
            # Combine title and description for better context.
            title = article.get('title', '')
            description = article.get('description', article.get('summary', ''))
            text = f"{title}\n{description}" if title and description else (title or description)

            doc = {
                'id': f"news_{article.get('id', i)}",
                'text': text,
                'metadata': {
                    'type': 'news',
                    'source': article.get('source', 'Unknown'),
                    'url': article.get('url', ''),
                    'published_at': article.get('published_at', ''),
                    'title': title
                }
            }
            documents.append(doc)

        logger.info(f"Loaded {len(documents)} news documents")
        return documents

    @staticmethod
    def load_security_tips() -> List[Dict]:
        """
        Load security tips as RAG documents.

        Returns:
            List of security tip documents
        """
        tips = [
            {
                'id': 'tip_001',
                'text': """MẠO LỪI PHISHING: Không bao giờ nhấp vào liên kết từ email không mong muốn.
Kiểm tra kỹ URL trước khi nhập thông tin nhạy cảm. Sử dụng công cụ kiểm tra URL để xác minh tính hợp lệ.
Các dấu hiệu lừa đảo: URL sai chính tả, tên miền đáng ngờ, yêu cầu hành động khẩn cấp, yêu cầu thông tin cá nhân.""",
                'metadata': {'type': 'security_tip', 'category': 'phishing', 'title': 'Phishing Protection'}
            },
            {
                'id': 'tip_002',
                'text': """MẬT KHẨU MẠNH: Sử dụng mật khẩu dài ít nhất 12 ký tự, kết hợp chữ hoa, chữ thường, số và ký tự đặc biệt.
Không sử dụng cùng mật khẩu cho nhiều tài khoản. Sử dụng password manager để quản lý mật khẩu.
Đổi mật khẩu định kỳ 3-6 tháng. Không chia sẻ mật khẩu với bất kỳ ai.""",
                'metadata': {'type': 'security_tip', 'category': 'password', 'title': 'Strong Passwords'}
            },
            {
                'id': 'tip_003',
                'text': """CVE VÀ LỖ HỔNG: Theo dõi thường xuyên các CVE mới. Đánh giá severity (CVSS score) để ưu tiên patch.
CVE (Common Vulnerabilities and Exposures) là hệ thống định danh lỗ hổng bảo mật.
CVSS score từ 0-10, trong đó 9.0-10.0 là Critical, 7.0-8.9 là High.
Cập nhật hệ điều hành và phần mềm thường xuyên để bảo mật.""",
                'metadata': {'type': 'security_tip', 'category': 'cve', 'title': 'CVE Management'}
            },
            {
                'id': 'tip_004',
                'text': """PHẢN ỨNG SỰ CỐ BẢO MẬT:
1. NGĂN CHẶN - Cô lập hệ thống bị ảnh hưởng khỏi mạng để ngăn chặn lan rộng.
2. PHÁT HIỆN - Xác định phạm vi tấn công và loại malware.
3. LOẠI BỎ - Xóa malware và patch lỗ hổng bị khai thác.
4. KHÔI PHỤC - Khôi phục hệ thống từ backup sạch và verify.
5. BÁO CÁO - Ghi log chi tiết và báo cáo sự cố theo quy định.""",
                'metadata': {'type': 'security_tip', 'category': 'incident_response', 'title': 'Incident Response'}
            },
            {
                'id': 'tip_005',
                'text': """XÁC THỰC 2 YẾU TỐ (2FA/MFA): Bật 2FA cho tất cả các tài khoản quan trọng.
Sử dụng authenticator app thay vì SMS (an toàn hơn).
Các phương pháp 2FA: TOTP app (Google Authenticator), Hardware token (YubiKey), Biometric.
2FA bảo vệ ngay cả khi mật khẩu bị lộ.""",
                'metadata': {'type': 'security_tip', 'category': 'authentication', 'title': 'Two-Factor Authentication'}
            },
            {
                'id': 'tip_006',
                'text': """RANSOMWARE: Backup dữ liệu định kỳ (3-2-1 rule: 3 bản sao, 2 loại media, 1 offsite).
Không mở email hoặc file từ nguồn không rõ. Giới chế quyền truy cập file (least privilege).
Cập nhật software và OS thường xuyên. Educate nhân viên về ransomware.
Nếu bị nhiễm: Ngắt kết nối mạng ngay, KHÔNG trả tiền, liên chuyên gia an ninh.""",
                'metadata': {'type': 'security_tip', 'category': 'malware', 'title': 'Ransomware Protection'}
            },
            {
                'id': 'tip_007',
                'text': """WI-FI SECURITY: Sử dụng WPA3 hoặc WPA2-AES cho Wi-Fi nhà và văn phòng.
Đổi mật khẩu Wi-Fi định kỳ. Tách guest network và main network.
Không sử dụng public Wi-Fi cho công việc nhạy cảm (banking, work).
Nếu phải dùng public Wi-Fi, dùng VPN để mã hóa kết nối.""",
                'metadata': {'type': 'security_tip', 'category': 'network', 'title': 'Wi-Fi Security'}
            },
            {
                'id': 'tip_008',
                'text': """SOCIAL ENGINEERING: Đừng tin những gì quá tốt để đúng. Verify requester identity.
Social engineering tấn công vào tâm lý và lòng tin, không phải kỹ thuật.
Các dấu hiệu: Urgency, pressure, request unusual, too good to be true.
Verify qua channel khác (gọi điện, gặp mặt) trước khi làm theo yêu cầu.""",
                'metadata': {'type': 'security_tip', 'category': 'social_engineering', 'title': 'Social Engineering Defense'}
            }
        ]
        logger.info(f"Loaded {len(tips)} security tips")
        return tips

    @staticmethod
    def load_cve_data(cve_records: List[Dict]) -> List[Dict]:
        """
        Convert CVE records to RAG documents.

        Args:
            cve_records: List of CVE record dicts from database

        Returns:
            List of CVE documents
        """
        documents = []
        for i, cve in enumerate(cve_records):
            cve_id = cve.get('cve_id', 'Unknown')
            description = cve.get('description', '')
            severity = cve.get('severity', 'Unknown')
            cvss_score = cve.get('cvss_score', 0)

            text = f"""CVE ID: {cve_id}
Severity: {severity}
CVSS Score: {cvss_score}
Description: {description}"""

            doc = {
                'id': f"cve_{cve_id}",
                'text': text,
                'metadata': {
                    'type': 'cve',
                    'cve_id': cve_id,
                    'severity': str(severity),
                    'cvss_score': float(cvss_score) if cvss_score else 0.0
                }
            }
            documents.append(doc)

        logger.info(f"Loaded {len(documents)} CVE documents")
        return documents

    @staticmethod
    def load_incident_response_procedures() -> List[Dict]:
        """
        Load incident response procedures as RAG documents.

        Returns:
            List of procedure documents
        """
        procedures = [
            {
                'id': 'procedure_001',
                'text': """QUY TRÌNH XỬ LÝ MALWARE:
1. Isolate: Ngắt máy bị nhiễm khỏi network
2. Identify: Chạy antivirus scan để xác định malware
3. Research: Tìm hiểu về loại malware đó
4. Clean: Dùng removal tool hoặc reinstall OS
5. Verify: Scan lại để đảm bảo sạch
6. Monitor: Theo dõi hoạt động bất thường sau đó
7. Report: Ghi log và báo cáo""",
                'metadata': {'type': 'procedure', 'category': 'malware', 'title': 'Malware Response'}
            },
            {
                'id': 'procedure_002',
                'text': """QUY TRÌNH XỬ LÝ DATA BREACH:
1. Contain: Ngăn chặn leak thêm dữ liệu
2. Assess: Xác định loại data bị leak và scope
3. Notify: Báo cho stakeholders, legal, authorities
4. Investigate: Forensic analysis để tìm root cause
5. Remediate: Patch lỗ hổng và implement controls
6. Communicate: Thông báo cho affected users
7. Review: Lessons learned và improve process""",
                'metadata': {'type': 'procedure', 'category': 'breach', 'title': 'Data Breach Response'}
            },
            {
                'id': 'procedure_003',
                'text': """QUY TRÌNH XỬ LÝ DDOS ATTACK:
1. Detect: Monitor traffic spike
2. Activate: Bật DDoS protection service
3. Filter: Filter malicious traffic
4. Scale: Scale up bandwidth/resources
5. Communicate: Update stakeholders
6. Analyze: Post-attack analysis
7. Prepare: Improve defenses for next time""",
                'metadata': {'type': 'procedure', 'category': 'ddos', 'title': 'DDoS Response'}
            }
        ]
        logger.info(f"Loaded {len(procedures)} incident response procedures")
        return procedures

    @staticmethod
    def load_all_knowledge() -> List[Dict]:
        """
        Load all available knowledge documents.

        Returns:
            Combined list of all document types
        """
        all_documents = []

        # Load security tips
        all_documents.extend(DocumentLoader.load_security_tips())

        # Load procedures
        all_documents.extend(DocumentLoader.load_incident_response_procedures())

        logger.info(f"Loaded total of {len(all_documents)} knowledge documents")
        return all_documents
