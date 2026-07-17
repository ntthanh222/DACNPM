"""Guarded backup/delete/restore recovery check for the isolated QA database."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from testing.scripts.qa_guard import guard_or_exit  # noqa: E402


REPORT = ROOT / "testing" / "reports" / "cybersec-assistant" / "QA_RECOVERY_REPORT.md"
BACKUP_DIR = ROOT / "testing" / "recovery" / "backups"


class CheckFailure(AssertionError):
    pass


def psql(sql: str) -> str:
    container = os.environ.get("QA_POSTGRES_CONTAINER", "cybersec-postgres-qa")
    db_name = os.environ.get("DB_NAME", "cybersec_qa")
    db_user = os.environ.get("DB_USER", "postgres")
    result = subprocess.run(
        ["docker", "exec", "-i", container, "psql", "-U", db_user, "-d", db_name, "-v", "ON_ERROR_STOP=1", "-X", "-q", "-t", "-A"],
        input=sql,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=True,
    )
    return result.stdout.strip()


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def row_count(asset_id: str) -> int:
    output = psql(f"SELECT COUNT(*) FROM public.assets WHERE id = {sql_literal(asset_id)};")
    return int(output or "0")


def main() -> int:
    guard_or_exit()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    REPORT.parent.mkdir(parents=True, exist_ok=True)

    asset_id = str(uuid4())
    name = f"qa-recovery-sentinel-{asset_id[:8]}"
    now = datetime.now(timezone.utc).isoformat()

    psql(
        f"""
        DELETE FROM public.assets WHERE name LIKE 'qa-recovery-sentinel-%';
        INSERT INTO public.assets (
            id, name, asset_type, hostname, environment, criticality,
            internet_exposure, status, notes, is_deleted, created_at, updated_at
        )
        VALUES (
            {sql_literal(asset_id)}, {sql_literal(name)}, 'server', {sql_literal(name + '.qa.local')},
            'qa', 'high', true, 'active', 'qa recovery sentinel',
            false, NOW(), NOW()
        );
        """
    )
    if row_count(asset_id) != 1:
        raise CheckFailure("sentinel insert failed")

    backup_json = psql(f"SELECT row_to_json(a)::text FROM public.assets a WHERE id = {sql_literal(asset_id)};")
    backup_path = BACKUP_DIR / f"qa_recovery_asset_{asset_id}.json"
    backup_path.write_text(json.dumps(json.loads(backup_json), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    psql(f"DELETE FROM public.assets WHERE id = {sql_literal(asset_id)};")
    if row_count(asset_id) != 0:
        raise CheckFailure("sentinel delete failed")

    restore_json = sql_literal(backup_path.read_text(encoding="utf-8"))
    psql(
        f"""
        INSERT INTO public.assets
        SELECT * FROM json_populate_record(NULL::public.assets, {restore_json}::json);
        """
    )
    if row_count(asset_id) != 1:
        raise CheckFailure("sentinel restore failed")

    restored = json.loads(psql(f"SELECT row_to_json(a)::text FROM public.assets a WHERE id = {sql_literal(asset_id)};"))
    if restored.get("name") != name or restored.get("status") != "active":
        raise CheckFailure("restored sentinel content mismatch")

    psql(f"DELETE FROM public.assets WHERE id = {sql_literal(asset_id)};")

    lines = [
        "# QA recovery report",
        "",
        f"Checked: `{now}`",
        "",
        "| Step | Evidence | Status |",
        "|---|---|---|",
        f"| Insert sentinel | `{asset_id}` | PASS |",
        f"| Backup sentinel row | `{backup_path}` | PASS |",
        "| Delete sentinel | count returned 0 | PASS |",
        "| Restore sentinel | count returned 1 | PASS |",
        "| Cleanup sentinel | hard deleted from QA assets | PASS |",
    ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("QA recovery PASS")
    print(f"- report: {REPORT}")
    print(f"- backup: {backup_path}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CheckFailure as exc:
        print(f"QA recovery FAIL: {exc}")
        raise SystemExit(1) from exc
