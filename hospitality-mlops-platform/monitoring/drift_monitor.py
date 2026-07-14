"""Evidently-based drift monitor service (illustrative blueprint).

Compares live inference traffic against the training reference window and
executes the tiered response policy in drift_thresholds.yaml. Endpoints and
credentials are placeholders.
"""
from dataclasses import dataclass
from enum import Enum


class DriftResponse(Enum):
    NONE = "none"
    WARN = "warn"
    RETRAIN = "retrain"
    HALT_AND_PAGE = "halt_and_page"


@dataclass
class DriftReport:
    model_name: str
    feature_wasserstein: float
    target_psi: float
    concept_page_hinkley_sigma: float


def classify(report: DriftReport) -> DriftResponse:
    """Tiered policy — most severe response wins.

    Concept drift means the world changed (e.g. structural shift in traveler
    behavior): automated pricing must not keep acting on a stale worldview,
    so it is paused and a human is paged rather than blindly retraining.
    """
    if report.concept_page_hinkley_sigma > 3.0:
        return DriftResponse.HALT_AND_PAGE
    if report.target_psi > 0.20:
        return DriftResponse.RETRAIN
    if report.feature_wasserstein > 0.15:
        return DriftResponse.WARN
    return DriftResponse.NONE


def dispatch(response: DriftResponse, report: DriftReport) -> None:
    if response is DriftResponse.RETRAIN:
        # POST to the Airflow REST API -> trigger dag_run: retrain_evaluate_promote
        raise NotImplementedError("Blueprint stub — endpoint omitted")
    if response is DriftResponse.HALT_AND_PAGE:
        # Flip the pricing agent's kill switch, then page on-call.
        raise NotImplementedError("Blueprint stub — endpoint omitted")
    if response is DriftResponse.WARN:
        # Annotate the model's dashboard panel.
        raise NotImplementedError("Blueprint stub — endpoint omitted")
