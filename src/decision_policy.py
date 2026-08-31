"""Contrato versionado para os limites da decisão governada da Forzy."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Mapping


_LIMIT_FIELDS = (
    "model_threshold",
    "display_threshold",
    "persistence_windows",
    "minimum_confidence",
    "minimum_completeness",
    "max_age_seconds",
    "future_tolerance_seconds",
)
_METADATA_FIELDS = ("policy_id", "version")
_ALLOWED_FIELDS = frozenset((*_LIMIT_FIELDS, *_METADATA_FIELDS))
_FIELD_ALIASES = {
    "threshold": "model_threshold",
    "exact_threshold": "model_threshold",
    "threshold_exact": "model_threshold",
    "anomaly_threshold": "model_threshold",
    "threshold_display": "display_threshold",
    "min_confidence": "minimum_confidence",
    "confidence_threshold": "minimum_confidence",
    "min_completeness": "minimum_completeness",
    "completeness_threshold": "minimum_completeness",
    "max_reading_age_seconds": "max_age_seconds",
    "max_age": "max_age_seconds",
    "future_tolerance": "future_tolerance_seconds",
    "windows": "persistence_windows",
}
DEFAULT_POLICY_PATH = Path(__file__).resolve().parents[1] / "config" / "decision_policy.json"


@dataclass(frozen=True)
class DecisionPolicy:
    """Limites que devem ser compartilhados pelo serviço e pela demonstração."""

    model_threshold: float
    display_threshold: float
    persistence_windows: int
    minimum_confidence: float
    minimum_completeness: float
    max_age_seconds: int
    future_tolerance_seconds: int
    policy_id: str = "forzy-decision-governance"
    version: str = "1.0"

    def __post_init__(self) -> None:
        for field in ("model_threshold", "display_threshold"):
            value = getattr(self, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(float(value))
                or float(value) <= 0
            ):
                raise ValueError(f"{field} deve ser positivo e finito")

        if (
            isinstance(self.persistence_windows, bool)
            or not isinstance(self.persistence_windows, int)
            or self.persistence_windows <= 0
        ):
            raise ValueError("persistence_windows deve ser um inteiro positivo")

        for field in ("minimum_confidence", "minimum_completeness"):
            value = getattr(self, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, Real)
                or not math.isfinite(float(value))
                or not 0 <= float(value) <= 1
            ):
                raise ValueError(f"{field} deve estar entre 0 e 1")

        for field in ("max_age_seconds", "future_tolerance_seconds"):
            value = getattr(self, field)
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
            ):
                raise ValueError(f"{field} deve ser um inteiro não negativo")

        if not isinstance(self.policy_id, str) or not self.policy_id.strip():
            raise ValueError("policy_id deve ser um texto não vazio")
        if not isinstance(self.version, str) or not self.version.strip():
            raise ValueError("version deve ser um texto não vazio")

    @property
    def exact_threshold(self) -> float:
        """Nome explícito do threshold usado no cálculo, sem arredondamento."""

        return self.model_threshold

    @property
    def threshold(self) -> float:
        """Alias compatível com chamadas antigas do serviço."""

        return self.model_threshold

    @property
    def threshold_exact(self) -> float:
        return self.model_threshold

    @property
    def threshold_display(self) -> float:
        return self.display_threshold

    @property
    def anomaly_threshold(self) -> float:
        return self.model_threshold

    @property
    def confidence_threshold(self) -> float:
        return self.minimum_confidence

    @property
    def min_confidence(self) -> float:
        return self.minimum_confidence

    @property
    def completeness_threshold(self) -> float:
        return self.minimum_completeness

    @property
    def min_completeness(self) -> float:
        return self.minimum_completeness

    @property
    def max_reading_age_seconds(self) -> int:
        return self.max_age_seconds

    @property
    def max_age(self) -> int:
        return self.max_age_seconds

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "DecisionPolicy":
        """Valida um objeto decodificado do JSON e cria o contrato imutável."""

        if not isinstance(payload, Mapping):
            raise ValueError("contrato de decisão deve ser um objeto JSON")

        unknown = sorted(set(payload) - _ALLOWED_FIELDS - set(_FIELD_ALIASES))
        if unknown:
            raise ValueError(f"campos desconhecidos no contrato: {', '.join(unknown)}")

        normalized = dict(payload)
        for alias, canonical in _FIELD_ALIASES.items():
            if alias not in normalized:
                continue
            if canonical in normalized and normalized[canonical] != normalized[alias]:
                raise ValueError(f"valores conflitantes para {canonical}")
            normalized[canonical] = normalized.pop(alias)

        missing = [field for field in _LIMIT_FIELDS if field not in normalized]
        if missing:
            raise ValueError(
                "campos obrigatórios ausentes no contrato: " + ", ".join(missing)
            )

        try:
            return cls(**normalized)
        except TypeError as exc:
            raise ValueError(f"contrato de decisão inválido: {exc}") from exc


def validate_decision_policy(payload: Mapping[str, Any]) -> DecisionPolicy:
    """Valida e devolve o contrato, útil para testes e integrações."""

    return DecisionPolicy.from_mapping(payload)


def load_decision_policy(path: str | Path) -> DecisionPolicy:
    """Carrega e valida a política JSON usada por toda a governança."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"não foi possível ler o contrato de decisão: {path}") from exc
    return validate_decision_policy(payload)


def load_default_decision_policy() -> DecisionPolicy:
    """Carrega a política oficial do repositório para chamadas sem injeção explícita."""

    return load_decision_policy(DEFAULT_POLICY_PATH)


load_policy = load_decision_policy
