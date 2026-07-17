# Backup & Restore Instructions

## Database Volumes
Volumes that must be preserved:
- `ncnpm_postgres_data`
- `ncnpm_redis_data`
- `ncnpm_chromadb_data`
- `ncnpm_prometheus_data`
- `ncnpm_grafana_data`
- Corresponding test volumes (`cybersec-assistant-test_*`)

## Backup Script (PowerShell)
```powershell
$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BackupDir = "D:\Backup\cybersec_$Timestamp"
New-Item -ItemType Directory -Force -Path $BackupDir

# Export volumes using a temporary Alpine container
docker run --rm -v ncnpm_postgres_data:/volume -v ${BackupDir}:/backup alpine tar -czf /backup/postgres_backup.tar.gz -C /volume .
docker run --rm -v ncnpm_redis_data:/volume -v ${BackupDir}:/backup alpine tar -czf /backup/redis_backup.tar.gz -C /volume .
docker run --rm -v ncnpm_chromadb_data:/volume -v ${BackupDir}:/backup alpine tar -czf /backup/chroma_backup.tar.gz -C /volume .
```

## Restore Script
```powershell
# Restore to a volume
docker run --rm -v ncnpm_postgres_data:/volume -v ${BackupDir}:/backup alpine sh -c "rm -rf /volume/* && tar -xzf /backup/postgres_backup.tar.gz -C /volume"
# Repeat for others
```
