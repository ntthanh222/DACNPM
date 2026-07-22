# RAG Diagnostics Report

- Collection Name: security_knowledge_qa_semantic_v1
- Embedding Backend: sentence-transformers
- Vector Dimension: 768
- Chunk Count (Total): 30

## Queries Diagnostics

### Query: Làm thế nào để bảo mật Ubuntu server?
- Expected IDs: ['doc1_ubuntu']
- Actual Top Retrieved IDs: ['doc1_ubuntu', 'doc10_backup', 'doc12_kubernetes']
- Detailed Retrieval:
  - Rank 1: ID=doc1_ubuntu_chunk_0, Title=doc1_ubuntu, Distance=0.4745885, Score=0.5254114999999999
  - Rank 2: ID=doc10_backup_chunk_0, Title=doc10_backup, Distance=0.47969028, Score=0.52030972
  - Rank 3: ID=doc12_kubernetes_chunk_0, Title=doc12_kubernetes, Distance=0.48579636, Score=0.5142036400000001

### Query: Cách tạo mật khẩu mạnh và quản lý chúng
- Expected IDs: ['doc2_password']
- Actual Top Retrieved IDs: ['doc2_password', 'doc2_password', 'doc1_ubuntu']
- Detailed Retrieval:
  - Rank 1: ID=doc2_password_chunk_0, Title=doc2_password, Distance=0.3854071, Score=0.6145929
  - Rank 2: ID=doc2_password_chunk_1, Title=doc2_password, Distance=0.48690233, Score=0.5130976700000001
  - Rank 3: ID=doc1_ubuntu_chunk_0, Title=doc1_ubuntu, Distance=0.49175745, Score=0.5082425500000001

### Query: Dấu hiệu của email lừa đảo phishing
- Expected IDs: ['doc3_phishing']
- Actual Top Retrieved IDs: ['doc3_phishing', 'doc3_phishing', 'doc18_pentest']
- Detailed Retrieval:
  - Rank 1: ID=doc3_phishing_chunk_0, Title=doc3_phishing, Distance=0.27282548, Score=0.7271745199999999
  - Rank 2: ID=doc3_phishing_chunk_1, Title=doc3_phishing, Distance=0.3668446, Score=0.6331553999999999
  - Rank 3: ID=doc18_pentest_chunk_0, Title=doc18_pentest, Distance=0.49939358, Score=0.50060642

### Query: Tra cứu thông tin lỗ hổng bảo mật CVE
- Expected IDs: ['doc4_cve']
- Actual Top Retrieved IDs: ['doc4_cve', 'doc16_network2', 'doc18_pentest']
- Detailed Retrieval:
  - Rank 1: ID=doc4_cve_chunk_0, Title=doc4_cve, Distance=0.3312909, Score=0.6687091000000001
  - Rank 2: ID=doc16_network2_chunk_0, Title=doc16_network2, Distance=0.38179177, Score=0.61820823
  - Rank 3: ID=doc18_pentest_chunk_0, Title=doc18_pentest, Distance=0.40480456, Score=0.59519544

### Query: Các bước ứng phó sự cố an ninh mạng
- Expected IDs: ['doc5_incident']
- Actual Top Retrieved IDs: ['doc16_network2', 'doc18_pentest', 'doc4_cve']
- Detailed Retrieval:
  - Rank 1: ID=doc16_network2_chunk_0, Title=doc16_network2, Distance=0.37695813, Score=0.62304187
  - Rank 2: ID=doc18_pentest_chunk_0, Title=doc18_pentest, Distance=0.39789817, Score=0.6021018300000001
  - Rank 3: ID=doc4_cve_chunk_0, Title=doc4_cve, Distance=0.4646473, Score=0.5353527

### Query: Phân vùng mạng và bảo mật database
- Expected IDs: ['doc6_network']
- Actual Top Retrieved IDs: ['doc16_network2', 'doc6_network', 'doc6_network']
- Detailed Retrieval:
  - Rank 1: ID=doc16_network2_chunk_0, Title=doc16_network2, Distance=0.36440915, Score=0.63559085
  - Rank 2: ID=doc6_network_chunk_1, Title=doc6_network, Distance=0.41449785, Score=0.5855021499999999
  - Rank 3: ID=doc6_network_chunk_0, Title=doc6_network, Distance=0.42060703, Score=0.57939297

### Query: Thiết lập xác thực hai lớp MFA bảo mật
- Expected IDs: ['doc7_mfa']
- Actual Top Retrieved IDs: ['doc7_mfa', 'doc14_zerotrust']
- Detailed Retrieval:
  - Rank 1: ID=doc7_mfa_chunk_0, Title=doc7_mfa, Distance=0.37334728, Score=0.62665272
  - Rank 2: ID=doc14_zerotrust_chunk_0, Title=doc14_zerotrust, Distance=0.48192048, Score=0.51807952

### Query: Ghi nhật ký hệ thống và giám sát bảo mật
- Expected IDs: ['doc8_logging']
- Actual Top Retrieved IDs: ['doc8_logging', 'doc16_network2', 'doc5_incident']
- Detailed Retrieval:
  - Rank 1: ID=doc8_logging_chunk_0, Title=doc8_logging, Distance=0.37646645, Score=0.62353355
  - Rank 2: ID=doc16_network2_chunk_0, Title=doc16_network2, Distance=0.40474045, Score=0.59525955
  - Rank 3: ID=doc5_incident_chunk_1, Title=doc5_incident, Distance=0.42449063, Score=0.57550937

### Query: Xác thực API bằng JWT an toàn
- Expected IDs: ['doc9_api']
- Actual Top Retrieved IDs: ['doc9_api']
- Detailed Retrieval:
  - Rank 1: ID=doc9_api_chunk_0, Title=doc9_api, Distance=0.252249, Score=0.747751

### Query: Sao lưu dữ liệu phòng chống mã độc mã hóa
- Expected IDs: ['doc10_backup']
- Actual Top Retrieved IDs: ['doc10_backup', 'doc9_api', 'doc12_kubernetes']
- Detailed Retrieval:
  - Rank 1: ID=doc10_backup_chunk_0, Title=doc10_backup, Distance=0.37529206, Score=0.62470794
  - Rank 2: ID=doc9_api_chunk_0, Title=doc9_api, Distance=0.46387482, Score=0.53612518
  - Rank 3: ID=doc12_kubernetes_chunk_0, Title=doc12_kubernetes, Distance=0.47308362, Score=0.5269163800000001

### Query: how to secure linux server hardening
- Expected IDs: ['doc1_ubuntu']
- Actual Top Retrieved IDs: ['doc1_ubuntu']
- Detailed Retrieval:
  - Rank 1: ID=doc1_ubuntu_chunk_0, Title=doc1_ubuntu, Distance=0.4733693, Score=0.5266307

### Query: indicator of phishing email redirects
- Expected IDs: ['doc3_phishing']
- Actual Top Retrieved IDs: ['doc3_phishing', 'doc3_phishing', 'doc15_edr']
- Detailed Retrieval:
  - Rank 1: ID=doc3_phishing_chunk_0, Title=doc3_phishing, Distance=0.25249302, Score=0.74750698
  - Rank 2: ID=doc3_phishing_chunk_1, Title=doc3_phishing, Distance=0.4356832, Score=0.5643168000000001
  - Rank 3: ID=doc15_edr_chunk_0, Title=doc15_edr, Distance=0.48318508, Score=0.5168149200000001

### Query: incident response containment isolate
- Expected IDs: ['doc5_incident']
- Actual Top Retrieved IDs: ['doc5_incident', 'doc19_ir2']
- Detailed Retrieval:
  - Rank 1: ID=doc5_incident_chunk_0, Title=doc5_incident, Distance=0.33931577, Score=0.66068423
  - Rank 2: ID=doc19_ir2_chunk_0, Title=doc19_ir2, Distance=0.37948573, Score=0.6205142699999999

### Query: JWT api secure authentication HTTPS
- Expected IDs: ['doc9_api']
- Actual Top Retrieved IDs: ['doc9_api', 'doc14_zerotrust']
- Detailed Retrieval:
  - Rank 1: ID=doc9_api_chunk_0, Title=doc9_api, Distance=0.23319289, Score=0.76680711
  - Rank 2: ID=doc14_zerotrust_chunk_0, Title=doc14_zerotrust, Distance=0.49529415, Score=0.50470585

### Query: backup offline tested restore decryption key
- Expected IDs: ['doc10_backup']
- Actual Top Retrieved IDs: ['doc10_backup']
- Detailed Retrieval:
  - Rank 1: ID=doc10_backup_chunk_0, Title=doc10_backup, Distance=0.4529559, Score=0.5470440999999999

