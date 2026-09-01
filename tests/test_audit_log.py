import json

from src.audit_log import append_audit_record


def test_append_audit_record_preserves_previous_json_lines(tmp_path):
    audit_path = tmp_path / "runtime" / "handoff_audit.jsonl"

    append_audit_record(audit_path, {"alert_id": "ALT-001", "decision": "Validado"})
    append_audit_record(audit_path, {"alert_id": "ALT-002", "decision": "Rejeitado"})

    records = [
        json.loads(line)
        for line in audit_path.read_text(encoding="utf-8").splitlines()
    ]
    assert records == [
        {"alert_id": "ALT-001", "decision": "Validado"},
        {"alert_id": "ALT-002", "decision": "Rejeitado"},
    ]
