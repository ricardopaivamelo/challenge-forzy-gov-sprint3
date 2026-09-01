"""Decisão determinística de governança e Circuit Breaker da Forzy."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
import math
from typing import Mapping

from src.decision_policy import DecisionPolicy, load_default_decision_policy
from src.governance_contracts import MetricContract, SensorAssessment


@dataclass(frozen=True)
class GovernanceDecision:
    motor_id: int
    timestamp: str
    status: str
    automatic_action: str
    circuit_breaker_open: bool
    breaker_reasons: tuple[str, ...]
    sensor_states: dict[str, str]
    sensor_assessments: dict[str, dict[str, object]]
    anomaly_score: float
    model_threshold: float
    persistent: bool
    consecutive_anomalous_windows: int
    classifier_confidence: float | None
    requires_human: bool
    handoff: dict[str, object] | None
    display_threshold: float | None = None
    policy_version: str | None = None


def _as_aware_datetime(value: str | datetime) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _blocked_decision(
    *,
    motor_id: int,
    timestamp: datetime,
    reasons: list[str],
    assessments: dict[str, SensorAssessment],
    score: float,
    threshold: float,
    persistent: bool,
    consecutive_anomalous_windows: int,
    classifier_confidence: float | None,
    policy: DecisionPolicy,
) -> GovernanceDecision:
    evidence = {
        "sensor_states": {field: item.state for field, item in assessments.items()},
        "anomaly_score": score,
        "model_threshold": threshold,
        "display_threshold": policy.display_threshold,
        "persistent": persistent,
        "consecutive_anomalous_windows": consecutive_anomalous_windows,
        "persistence_windows": policy.persistence_windows,
        "minimum_confidence": policy.minimum_confidence,
        "minimum_completeness": policy.minimum_completeness,
        "max_age_seconds": policy.max_age_seconds,
        "future_tolerance_seconds": policy.future_tolerance_seconds,
        "policy_version": policy.version,
        "breaker_reasons": list(reasons),
    }
    return GovernanceDecision(
        motor_id=int(motor_id),
        timestamp=timestamp.isoformat(),
        status="blocked",
        automatic_action=(
            "Bloquear o alerta decisório, registrar a inconsistência e solicitar "
            "validação humana."
        ),
        circuit_breaker_open=True,
        breaker_reasons=tuple(reasons),
        sensor_states={field: item.state for field, item in assessments.items()},
        sensor_assessments={field: asdict(item) for field, item in assessments.items()},
        anomaly_score=score,
        model_threshold=threshold,
        persistent=persistent,
        consecutive_anomalous_windows=consecutive_anomalous_windows,
        classifier_confidence=classifier_confidence,
        requires_human=True,
        handoff={
            "status": "pending",
            "recipient": "Engenheiro de Manutenção",
            "reason": "Circuit Breaker acionado",
            "evidence": evidence,
        },
        display_threshold=policy.display_threshold,
        policy_version=policy.version,
    )


def evaluate_governance(
    *,
    motor_id: int,
    readings: Mapping[str, object],
    units: Mapping[str, str],
    timestamp: str | datetime,
    now: str | datetime,
    score: float,
    consecutive_anomalous_windows: int,
    classifier_confidence: float | None,
    completeness_ratio: float,
    duplicate_timestamp: bool,
    model_available: bool,
    contracts: Mapping[str, MetricContract],
    policy: DecisionPolicy | None = None,
    threshold: float | None = None,
) -> GovernanceDecision:
    """Aplica contratos, incerteza e handoff sem comandar equipamento físico."""

    numeric_score = float(score)
    if policy is not None and not isinstance(policy, DecisionPolicy):
        raise TypeError("policy deve ser uma instância de DecisionPolicy")
    if policy is None:
        policy = load_default_decision_policy()
        if threshold is not None:
            try:
                legacy_threshold = float(threshold)
            except (TypeError, ValueError) as exc:
                raise ValueError("threshold do modelo deve ser positivo e finito") from exc
            policy = replace(
                policy,
                model_threshold=legacy_threshold,
                display_threshold=legacy_threshold,
            )
    numeric_threshold = float(policy.model_threshold)
    if not math.isfinite(numeric_threshold) or numeric_threshold <= 0:
        raise ValueError("threshold do modelo deve ser positivo e finito")
    if not math.isfinite(numeric_score):
        raise ValueError("score do modelo deve ser finito")
    if classifier_confidence is not None and not 0 <= classifier_confidence <= 1:
        raise ValueError("classifier_confidence deve estar entre 0 e 1")
    if (
        isinstance(consecutive_anomalous_windows, bool)
        or not isinstance(consecutive_anomalous_windows, int)
        or consecutive_anomalous_windows < 0
    ):
        raise ValueError(
            "consecutive_anomalous_windows deve ser um inteiro não negativo"
        )
    persistent = consecutive_anomalous_windows >= policy.persistence_windows

    event_time = _as_aware_datetime(timestamp)
    reference_time = _as_aware_datetime(now)
    reasons: list[str] = []
    assessments: dict[str, SensorAssessment] = {}

    for field in policy.required_sensor_fields:
        contract = contracts.get(field)
        if contract is None:
            reasons.append(f"Contrato obrigatório ausente: {field}.")
            continue
        if contract.field != field:
            reasons.append(
                f"Contrato incompatível em {field}: declara o campo {contract.field}."
            )
        if contract.version != policy.metric_contract_version:
            reasons.append(
                f"Versão incompatível do contrato {field}: recebido "
                f"{contract.version!r}, esperado {policy.metric_contract_version!r}."
            )
        if field not in readings or readings[field] is None:
            reasons.append(f"Sensor obrigatório ausente: {field}.")
            continue
        try:
            assessments[field] = contract.classify(float(readings[field]))
        except (TypeError, ValueError) as exc:
            if isinstance(readings[field], str):
                reasons.append(f"Valor não numérico em {field}.")
            else:
                reasons.append(str(exc))
        received_unit = units.get(field)
        if received_unit != contract.unit:
            reasons.append(
                f"Unidade incompatível em {field}: recebido {received_unit!r}, "
                f"esperado {contract.unit!r}."
            )

    age_seconds = (reference_time - event_time).total_seconds()
    if age_seconds > policy.max_age_seconds:
        reasons.append(f"Leitura desatualizada há {age_seconds / 60:.1f} minutos.")
    if age_seconds < -policy.future_tolerance_seconds:
        reasons.append("Timestamp da leitura está no futuro.")
    if duplicate_timestamp:
        reasons.append("Timestamp duplicado para o motor.")
    if (
        not math.isfinite(float(completeness_ratio))
        or completeness_ratio < policy.minimum_completeness
    ):
        reasons.append(
            "Completude da janela abaixo de "
            f"{policy.minimum_completeness:.0%}: {float(completeness_ratio):.1%}."
        )
    if not model_available:
        reasons.append("Artefato ou versão do modelo indisponível.")

    if reasons:
        return _blocked_decision(
            motor_id=motor_id,
            timestamp=event_time,
            reasons=reasons,
            assessments=assessments,
            score=numeric_score,
            threshold=numeric_threshold,
            persistent=persistent,
            consecutive_anomalous_windows=consecutive_anomalous_windows,
            classifier_confidence=classifier_confidence,
            policy=policy,
        )

    sensor_states = {field: item.state for field, item in assessments.items()}
    physical_evidence = any(state in {"attention", "critical"} for state in sensor_states.values())
    physical_critical = any(state == "critical" for state in sensor_states.values())
    model_anomaly = numeric_score >= numeric_threshold

    uncertainty_reasons: list[str] = []
    if model_anomaly and not persistent:
        window_count = {
            1: "uma",
            2: "duas",
            3: "três",
        }.get(policy.persistence_windows, str(policy.persistence_windows))
        uncertainty_reasons.append(
            "Anomalia ainda não atingiu a persistência de "
            f"{window_count} janelas."
        )
    if (
        model_anomaly
        and classifier_confidence is not None
        and classifier_confidence < policy.minimum_confidence
    ):
        uncertainty_reasons.append(
            "Confiança do classificador abaixo de "
            f"{policy.minimum_confidence:.0%}: {classifier_confidence:.1%}."
        )
    if model_anomaly and not physical_evidence:
        uncertainty_reasons.append(
            "Divergência entre score anômalo e sensores dentro dos limites físicos."
        )
    if physical_critical and not model_anomaly:
        uncertainty_reasons.append(
            "Divergência entre sensor crítico e score do modelo abaixo do threshold."
        )

    if uncertainty_reasons:
        return _blocked_decision(
            motor_id=motor_id,
            timestamp=event_time,
            reasons=uncertainty_reasons,
            assessments=assessments,
            score=numeric_score,
            threshold=numeric_threshold,
            persistent=persistent,
            consecutive_anomalous_windows=consecutive_anomalous_windows,
            classifier_confidence=classifier_confidence,
            policy=policy,
        )

    if model_anomaly and physical_evidence:
        status = "alert"
        action = "Registrar alerta confirmado e solicitar inspeção técnica humana."
        requires_human = True
        handoff = {
            "status": "pending",
            "recipient": "Engenheiro de Manutenção",
            "reason": "Anomalia persistente com evidência física",
            "evidence": {
                "sensor_states": sensor_states,
                "anomaly_score": numeric_score,
                "model_threshold": numeric_threshold,
                "display_threshold": policy.display_threshold,
                "persistent": persistent,
                "consecutive_anomalous_windows": consecutive_anomalous_windows,
                "persistence_windows": policy.persistence_windows,
                "minimum_confidence": policy.minimum_confidence,
                "policy_version": policy.version,
            },
        }
    elif physical_evidence:
        status = "attention"
        action = "Destacar o desvio e manter monitoramento sem comandar parada."
        requires_human = False
        handoff = None
    else:
        status = "normal"
        action = "Registrar leitura e manter monitoramento de rotina."
        requires_human = False
        handoff = None

    return GovernanceDecision(
        motor_id=int(motor_id),
        timestamp=event_time.isoformat(),
        status=status,
        automatic_action=action,
        circuit_breaker_open=False,
        breaker_reasons=(),
        sensor_states=sensor_states,
        sensor_assessments={field: asdict(item) for field, item in assessments.items()},
        anomaly_score=numeric_score,
        model_threshold=numeric_threshold,
        persistent=persistent,
        consecutive_anomalous_windows=consecutive_anomalous_windows,
        classifier_confidence=classifier_confidence,
        requires_human=requires_human,
        handoff=handoff,
        display_threshold=policy.display_threshold,
        policy_version=policy.version,
    )
