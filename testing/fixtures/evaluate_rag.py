import os
import json
from uuid import uuid4
from typing import List, Dict, Any

# Ensure directories exist
os.makedirs("testing/fixtures/rag_corpus", exist_ok=True)

# 1. Generate 10 Corpus Documents
corpus = {
    "doc1_ubuntu": ("ubuntu_hardening", "Hardening Ubuntu servers by enforcing MFA, disabling unused ports, configuring SSH key access, disabling root login, and setting up firewall allowlists. Focus on regular updates and disabling compilers for normal users."),
    "doc2_password": ("password_security", "Create strong passwords by using at least 16 characters, uppercase and lowercase letters, symbols, numbers, passphrase patterns, and saving them in password managers. Never write passwords in plaintext logs."),
    "doc3_phishing": ("phishing_indicators", "Identify phishing indicators by analyzing sender addresses, weird redirects, certificate issues, and urgent call-to-action phrasing. Sandboxing URLs before clicking prevents credential theft."),
    "doc4_cve": ("cve_basics", "Common Vulnerabilities and Exposures (CVE) provides standard names for publicly known security vulnerabilities to prioritize patching. Critical CVEs need immediate patching within 24 hours."),
    "doc5_incident": ("incident_response", "Incident response stages include containment to isolate systems, eradication of root causes, recovery from secure backups, and documenting post-incident lessons. Preserving audit logs is crucial."),
    "doc6_network": ("network_segmentation", "Implement network segmentation to separate database environments from web app frontends and limit lateral movement during breach. Use firewalls and microsegmentation rules."),
    "doc7_mfa": ("mfa_auth", "Multi-Factor Authentication (MFA) requires two or more verification factors: password, hardware token, biometric, or authenticator app. Avoid SMS-based MFA due to SIM swapping risk."),
    "doc8_logging": ("logging_monitoring", "Centralized logging and active security monitoring help detect suspicious SSRF attempts, brute-force logins, and unauthorized data transfers. Keep audit logs safe from mutation."),
    "doc9_api": ("secure_api_auth", "Secure API authentication using cryptographically signed JSON Web Tokens (JWT), short expiration times, and secure HTTPS transport. Enforce roles in the backend, not in the frontend."),
    "doc10_backup": ("backup_recovery", "Maintain tested, encrypted, versioned offline backups to quickly recover from ransomware without paying ransoms. Keep backups isolated from the primary network.")
}

for doc_id, (topic, text) in corpus.items():
    with open(f"testing/fixtures/rag_corpus/{doc_id}.txt", "w", encoding="utf-8") as f:
        f.write(text)

# 2. Generate 15 Golden Queries
golden_queries = [
    {
        "query": "Làm thế nào để bảo mật Ubuntu server?",
        "expected_document_ids": ["doc1_ubuntu"],
        "expected_topic": "ubuntu_hardening",
        "must_not_retrieve": ["doc9_api"]
    },
    {
        "query": "Cách tạo mật khẩu mạnh và quản lý chúng",
        "expected_document_ids": ["doc2_password"],
        "expected_topic": "password_security",
        "must_not_retrieve": ["doc1_ubuntu"]
    },
    {
        "query": "Dấu hiệu của email lừa đảo phishing",
        "expected_document_ids": ["doc3_phishing"],
        "expected_topic": "phishing_indicators",
        "must_not_retrieve": ["doc10_backup"]
    },
    {
        "query": "Tra cứu thông tin lỗ hổng bảo mật CVE",
        "expected_document_ids": ["doc4_cve"],
        "expected_topic": "cve_basics",
        "must_not_retrieve": ["doc6_network"]
    },
    {
        "query": "Các bước ứng phó sự cố an ninh mạng",
        "expected_document_ids": ["doc5_incident"],
        "expected_topic": "incident_response",
        "must_not_retrieve": ["doc2_password"]
    },
    {
        "query": "Phân vùng mạng và bảo mật database",
        "expected_document_ids": ["doc6_network"],
        "expected_topic": "network_segmentation",
        "must_not_retrieve": ["doc4_cve"]
    },
    {
        "query": "Thiết lập xác thực hai lớp MFA bảo mật",
        "expected_document_ids": ["doc7_mfa"],
        "expected_topic": "mfa_auth",
        "must_not_retrieve": ["doc8_logging"]
    },
    {
        "query": "Ghi nhật ký hệ thống và giám sát bảo mật",
        "expected_document_ids": ["doc8_logging"],
        "expected_topic": "logging_monitoring",
        "must_not_retrieve": ["doc1_ubuntu"]
    },
    {
        "query": "Xác thực API bằng JWT an toàn",
        "expected_document_ids": ["doc9_api"],
        "expected_topic": "secure_api_auth",
        "must_not_retrieve": ["doc3_phishing"]
    },
    {
        "query": "Sao lưu dữ liệu phòng chống mã độc mã hóa",
        "expected_document_ids": ["doc10_backup"],
        "expected_topic": "backup_recovery",
        "must_not_retrieve": ["doc7_mfa"]
    },
    {
        "query": "how to secure linux server hardening",
        "expected_document_ids": ["doc1_ubuntu"],
        "expected_topic": "ubuntu_hardening",
        "must_not_retrieve": ["doc10_backup"]
    },
    {
        "query": "indicator of phishing email redirects",
        "expected_document_ids": ["doc3_phishing"],
        "expected_topic": "phishing_indicators",
        "must_not_retrieve": ["doc5_incident"]
    },
    {
        "query": "incident response containment isolate",
        "expected_document_ids": ["doc5_incident"],
        "expected_topic": "incident_response",
        "must_not_retrieve": ["doc9_api"]
    },
    {
        "query": "JWT api secure authentication HTTPS",
        "expected_document_ids": ["doc9_api"],
        "expected_topic": "secure_api_auth",
        "must_not_retrieve": ["doc4_cve"]
    },
    {
        "query": "backup offline tested restore decryption key",
        "expected_document_ids": ["doc10_backup"],
        "expected_topic": "backup_recovery",
        "must_not_retrieve": ["doc1_ubuntu"]
    }
]

with open("testing/fixtures/rag_golden_queries.json", "w", encoding="utf-8") as f:
    json.dump(golden_queries, f, ensure_ascii=False, indent=2)

print("Generated RAG corpus and 15 golden queries.")
