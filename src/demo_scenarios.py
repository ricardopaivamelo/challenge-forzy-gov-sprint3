"""Cenários determinísticos usados no dashboard, nas evidências e no vídeo."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping

from src.decision_policy import DecisionPolicy, load_decision_policy
from src.governance_contracts import MetricContract
from src.governance_service import GovernanceDecision, evaluate_governance


DEMO_TIME = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)
DEMO_UNITS = {
    "temperatura_c": "°C",
    "vibracao_mm_s": "mm/s",
    "aceleracao_g": "g",
}
DEFAULT_POLICY = load_decision_policy(
    Path(__file__).resolve().parents[1] / "config" / "decision_policy.json"
)


@dataclass(frozen=True)
class DemoScenario:
    description: str
    readings: dict[str, object]
    score: float
    persistent: bool
    classifier_confidence: float


def build_demo_scenarios(
    policy: DecisionPolicy | None = None,
) -> dict[str, DemoScenario]:
    active_policy = policy or DEFAULT_POLICY
    window_count = {
        1: "uma",
        2: "duas",
        3: "três",
    }.get(active_policy.persistence_windows, str(active_policy.persistence_windows))
    return {
        "Operação normal": DemoScenario(
            description="Sensores e modelo dentro do comportamento esperado.",
            readings={"temperatura_c": 70.0, "vibracao_mm_s": 2.0, "aceleracao_g": 0.08},
            score=0.50,
            persistent=False,
            classifier_confidence=0.96,
        ),
        "Faixa de atenção": DemoScenario(
            description="Temperatura requer acompanhamento, sem alerta decisório.",
            readings={"temperatura_c": 95.0, "vibracao_mm_s": 3.0, "aceleracao_g": 0.10},
            score=0.70,
            persistent=False,
            classifier_confidence=0.92,
        ),
        "Anomalia confirmada": DemoScenario(
            description=(
                "Score persistente por "
                f"{window_count} janelas e sensores críticos geram inspeção humana."
            ),
            readings={"temperatura_c": 102.0, "vibracao_mm_s": 9.8, "aceleracao_g": 0.21},
            score=1.30,
            persistent=True,
            classifier_confidence=0.94,
        ),
        "Circuit Breaker por dado inválido": DemoScenario(
            description="Valor inválido bloqueia o alerta e preserva a evidência.",
            readings={
                "temperatura_c": "sensor_error",
                "vibracao_mm_s": 9.8,
                "aceleracao_g": 0.21,
            },
            score=1.30,
            persistent=True,
            classifier_confidence=0.94,
        ),
        "Handoff por baixa confiança": DemoScenario(
            description="Candidato a alerta não recebe autonomia com confiança insuficiente.",
            readings={"temperatura_c": 102.0, "vibracao_mm_s": 9.8, "aceleracao_g": 0.21},
            score=1.30,
            persistent=True,
            classifier_confidence=0.72,
        ),
    }


def evaluate_demo_scenario(
    scenario: DemoScenario,
    contracts: Mapping[str, MetricContract],
    *,
    motor_id: int = 7,
    policy: DecisionPolicy | None = None,
) -> GovernanceDecision:
    active_policy = policy or DEFAULT_POLICY
    return evaluate_governance(
        motor_id=motor_id,
        readings=scenario.readings,
        units=DEMO_UNITS,
        timestamp=DEMO_TIME,
        now=DEMO_TIME,
        score=scenario.score,
        persistent=scenario.persistent,
        classifier_confidence=scenario.classifier_confidence,
        completeness_ratio=1.0,
        duplicate_timestamp=False,
        model_available=True,
        contracts=contracts,
        policy=active_policy,
    )
