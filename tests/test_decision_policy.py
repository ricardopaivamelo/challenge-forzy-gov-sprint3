import json
from pathlib import Path

import pytest

from src.decision_policy import DecisionPolicy, load_decision_policy


ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = ROOT / "config" / "decision_policy.json"


def test_loads_the_versioned_governance_policy_values():
    policy = load_decision_policy(POLICY_PATH)

    assert policy.model_threshold == 0.9512501159120564
    assert policy.exact_threshold == 0.9512501159120564
    assert policy.display_threshold == 0.9513
    assert policy.persistence_windows == 3
    assert policy.minimum_confidence == 0.85
    assert policy.minimum_completeness == 0.90
    assert policy.max_age_seconds == 300
    assert policy.future_tolerance_seconds == 60
    assert policy.metric_contract_version == "1.0"
    assert policy.required_sensor_fields == (
        "temperatura_c",
        "vibracao_mm_s",
        "aceleracao_g",
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("model_threshold", 0),
        ("display_threshold", -0.01),
        ("persistence_windows", 0),
        ("minimum_confidence", 1.01),
        ("minimum_completeness", -0.01),
        ("max_age_seconds", -1),
        ("future_tolerance_seconds", -1),
    ],
)
def test_policy_rejects_invalid_limits(field, value):
    values = {
        "model_threshold": 0.9512501159120564,
        "display_threshold": 0.9513,
        "persistence_windows": 3,
        "minimum_confidence": 0.85,
        "minimum_completeness": 0.90,
        "max_age_seconds": 300,
        "future_tolerance_seconds": 60,
        "metric_contract_version": "1.0",
        "required_sensor_fields": (
            "temperatura_c",
            "vibracao_mm_s",
            "aceleracao_g",
        ),
    }
    values[field] = value

    with pytest.raises(ValueError):
        DecisionPolicy(**values)


def test_policy_loader_rejects_missing_or_unknown_contract_fields(tmp_path):
    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    payload.pop("model_threshold")
    missing_path = tmp_path / "missing.json"
    missing_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="model_threshold"):
        load_decision_policy(missing_path)

    payload = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    payload["unexpected"] = True
    unknown_path = tmp_path / "unknown.json"
    unknown_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="unexpected"):
        load_decision_policy(unknown_path)


def test_policy_exposes_compatibility_names_for_governance_callers():
    policy = load_decision_policy(POLICY_PATH)

    assert policy.threshold == policy.model_threshold
    assert policy.confidence_threshold == policy.minimum_confidence
    assert policy.completeness_threshold == policy.minimum_completeness
    assert policy.max_reading_age_seconds == policy.max_age_seconds


def test_provenance_records_immutable_genai_source_and_limited_model_claim():
    provenance = json.loads(
        (ROOT / "results" / "provenance.json").read_text(encoding="utf-8")
    )

    assert provenance["repository"].endswith("challenge-forzy-genai-sprint3")
    assert provenance["commit"] == "7ff33d0839593e0f49bf55d70e33b6bc4b25c08e"
    assert provenance["source"] == "models/anomaly_metrics.json"
    assert provenance["source_sha256"] == (
        "4caa11177d4056d8ababa13de5d90d249c8cf7f6eb4175a82aae63bb3432925b"
    )
    assert provenance["selected_model"] == "Autoencoder"
    assert provenance["model_threshold"] == 0.9512501159120564
    assert provenance["best_anomaly_model_in_source"] == "statistical"
    rationale = provenance["selection_rationale"]
    assert "FPR" in rationale
    assert "reconstrução" in rationale
    assert "demonstrador" in rationale
    assert "melhor modelo geral" in rationale
