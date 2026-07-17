# QA recovery report

Checked: `2026-07-18T21:38:27.119997+00:00`

| Step | Evidence | Status |
|---|---|---|
| Insert sentinel | `08ef9878-f58b-405c-bc9d-a1a84da3bebb` | PASS |
| Backup sentinel row | `D:\Đồ án CNPM\testing\recovery\backups\qa_recovery_asset_08ef9878-f58b-405c-bc9d-a1a84da3bebb.json` | PASS |
| Delete sentinel | count returned 0 | PASS |
| Restore sentinel | count returned 1 | PASS |
| Cleanup sentinel | hard deleted from QA assets | PASS |
