"""Adaptação de dados técnicos para apresentação estável no dashboard."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

from src.decision_policy import DecisionPolicy, load_default_decision_policy
from src.governance_contracts import MetricContract


def build_contract_rows(
    *,
    contracts: Mapping[str, MetricContract],
    readings: Mapping[str, object],
    sensor_states: Mapping[str, str],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for field, contract in contracts.items():
        rows.append(
            {
                "Métrica": contract.label,
                "Valor": str(readings.get(field)),
                "Unidade": contract.unit,
                "Atenção": contract.attention_min,
                "Crítico": contract.critical_min,
                "Estado": sensor_states.get(field, "invalid"),
                "Versão": contract.version,
            }
        )
    return rows


def build_handoff_record(
    *,
    alert_id: str,
    motor_id: int,
    scenario_name: str,
    decision: str,
    justification: str,
    recorded_at: datetime,
    readings: Mapping[str, object],
    anomaly_score: float,
    classifier_confidence: float | None,
    breaker_reasons: list[str] | tuple[str, ...],
    contract_versions: Mapping[str, str],
    model_threshold: float | None = None,
    minimum_confidence: float | None = None,
    policy: DecisionPolicy | None = None,
) -> dict[str, object]:
    """Cria o registro autocontido da validação humana para auditoria da demo."""

    timestamp = recorded_at
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    else:
        timestamp = timestamp.astimezone(timezone.utc)

    if policy is not None and not isinstance(policy, DecisionPolicy):
        raise TypeError("policy deve ser uma instância de DecisionPolicy")
    if policy is not None:
        effective_model_threshold = policy.model_threshold
        effective_display_threshold = policy.display_threshold
        effective_minimum_confidence = policy.minimum_confidence
        effective_persistence_windows = policy.persistence_windows
        policy_version = policy.version
    else:
        if model_threshold is None or minimum_confidence is None:
            raise ValueError(
                "policy ou model_threshold e minimum_confidence deve ser informado"
            )
        effective_model_threshold = float(model_threshold)
        effective_display_threshold = float(model_threshold)
        effective_minimum_confidence = float(minimum_confidence)
        default_policy = load_default_decision_policy()
        effective_persistence_windows = default_policy.persistence_windows
        policy_version = default_policy.version

    return {
        "alert_id": alert_id,
        "motor_id": int(motor_id),
        "scenario": scenario_name,
        "recorded_at": timestamp.isoformat(),
        "decision": decision,
        "justification": justification,
        "evidence": {
            "readings": dict(readings),
            "anomaly_score": float(anomaly_score),
            "model_threshold": float(effective_model_threshold),
            "display_threshold": float(effective_display_threshold),
            "classifier_confidence": classifier_confidence,
            "minimum_confidence": float(effective_minimum_confidence),
            "persistence_windows": effective_persistence_windows,
            "policy_version": policy_version,
            "breaker_reasons": list(breaker_reasons),
            "contract_versions": dict(contract_versions),
        },
    }
