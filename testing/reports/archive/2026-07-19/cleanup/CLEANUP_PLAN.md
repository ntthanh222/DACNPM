Path hoặc Docker object: `__pycache__`, `*.pyc`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache`
Current size: Unknown (small but many)
Classification: A. Có thể xóa an toàn
Reason: Temporary cache files
Referenced by: N/A
Backup required: No
Regeneration command: Run python / pytest / mypy
Planned action: Remove
Risk: Low

Path hoặc Docker object: Dangling Docker Images and Build Cache
Current size: Several GBs
Classification: A. Có thể xóa an toàn
Reason: Dangling artifacts
Referenced by: N/A
Backup required: No
Regeneration command: docker build
Planned action: `docker image prune -f`, `docker builder prune -f`
Risk: Low

Path hoặc Docker object: Anonymous Docker Volumes
Current size: Unknown
Classification: A. Có thể xóa an toàn
Reason: Unused volumes created by Docker
Referenced by: N/A
Backup required: No
Regeneration command: recreate containers
Planned action: `docker volume rm` on non-named, unused volumes
Risk: Medium (make sure they are unused)

Path hoặc Docker object: `testing/reports` and `test-reports` (duplicate/old)
Current size: Unknown
Classification: C. Nên archive
Reason: Old reports can be archived, keep latest
Referenced by: N/A
Backup required: Archive
Regeneration command: N/A
Planned action: Keep latest, archive others
Risk: Low

Path hoặc Docker object: Unused dependencies in `backend/requirements.txt` / `package.json`
Current size: N/A
Classification: B. Có thể tái tạo nhưng phải xác minh
Reason: Code rot
Referenced by: N/A
Backup required: No
Regeneration command: `pip install` / `npm install`
Planned action: Identify and remove
Risk: High (needs testing)
