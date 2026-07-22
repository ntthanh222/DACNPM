# RAG System Evaluation

## 1. Summary Metrics
* **Total Queries**: 15
* **Embedding Backend**: sentence-transformers

## Overall Metrics

| Metric | Value | Target |
| :--- | :--- | :--- |
| **Recall@1** | 0.8667 | - |
| **Recall@3** | 0.9333 | >= 0.8000 |
| **MRR** | 0.9000 | >= 0.6500 |
| **Empty Retrieval Rate** | 0.0000 | 0.0000 |
| **Duplicate Retrieval Rate** | 0.2667 | 0.0000 |
| **Irrelevant Retrieval Rate** | 0.0667 | 0.0000 |

## Detailed Query Results

| Query | Expected ID | Retrieved IDs | Recall@3 | MRR |
| :--- | :--- | :--- | :--- | :--- |
| Làm thế nào để bảo mật Ubuntu server? | `['doc1_ubuntu']` | `['doc1_ubuntu', 'doc10_backup', 'doc12_kubernetes']` | 1.00 | 1.00 |
| Cách tạo mật khẩu mạnh và quản lý chúng | `['doc2_password']` | `['doc2_password', 'doc2_password', 'doc1_ubuntu']` | 1.00 | 1.00 |
| Dấu hiệu của email lừa đảo phishing | `['doc3_phishing']` | `['doc3_phishing', 'doc3_phishing', 'doc18_pentest']` | 1.00 | 1.00 |
| Tra cứu thông tin lỗ hổng bảo mật CVE | `['doc4_cve']` | `['doc4_cve', 'doc16_network2', 'doc18_pentest']` | 1.00 | 1.00 |
| Các bước ứng phó sự cố an ninh mạng | `['doc5_incident']` | `['doc16_network2', 'doc18_pentest', 'doc4_cve']` | 0.00 | 0.00 |
| Phân vùng mạng và bảo mật database | `['doc6_network']` | `['doc16_network2', 'doc6_network', 'doc6_network']` | 1.00 | 0.50 |
| Thiết lập xác thực hai lớp MFA bảo mật | `['doc7_mfa']` | `['doc7_mfa', 'doc14_zerotrust']` | 1.00 | 1.00 |
| Ghi nhật ký hệ thống và giám sát bảo mật | `['doc8_logging']` | `['doc8_logging', 'doc16_network2', 'doc5_incident']` | 1.00 | 1.00 |
| Xác thực API bằng JWT an toàn | `['doc9_api']` | `['doc9_api']` | 1.00 | 1.00 |
| Sao lưu dữ liệu phòng chống mã độc mã hóa | `['doc10_backup']` | `['doc10_backup', 'doc9_api', 'doc12_kubernetes']` | 1.00 | 1.00 |
| how to secure linux server hardening | `['doc1_ubuntu']` | `['doc1_ubuntu']` | 1.00 | 1.00 |
| indicator of phishing email redirects | `['doc3_phishing']` | `['doc3_phishing', 'doc3_phishing', 'doc15_edr']` | 1.00 | 1.00 |
| incident response containment isolate | `['doc5_incident']` | `['doc5_incident', 'doc19_ir2']` | 1.00 | 1.00 |
| JWT api secure authentication HTTPS | `['doc9_api']` | `['doc9_api', 'doc14_zerotrust']` | 1.00 | 1.00 |
| backup offline tested restore decryption key | `['doc10_backup']` | `['doc10_backup']` | 1.00 | 1.00 |
