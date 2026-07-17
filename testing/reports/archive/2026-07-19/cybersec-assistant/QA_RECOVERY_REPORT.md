# QA recovery report

Checked: `2026-07-18T21:35:07.669538+00:00`

| Step | Evidence | Status |
|---|---|---|
| Insert sentinel | `e2e4506b-db40-47fa-85ad-ee956529524c` | PASS |
| Backup sentinel row | `D:\Đồ án CNPM\testing\recovery\backups\qa_recovery_asset_e2e4506b-db40-47fa-85ad-ee956529524c.json` | PASS |
| Delete sentinel | count returned 0 | PASS |
| Restore sentinel | count returned 1 | PASS |
| Cleanup sentinel | hard deleted from QA assets | PASS |
