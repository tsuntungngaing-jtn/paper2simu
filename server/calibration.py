"""Calibration provenance. Fitted values never become reported. LITERATURE_ADAPTED."""
from __future__ import annotations

from copy import deepcopy
from typing import Any


class CalibrationLedger:
    """Track fitted parameters.

    A different ``claim_id`` is necessary but never sufficient for independent
    validation. Callers must record hold-out partition, frozen model revision,
    hold-out run identity and score evidence before ``VALIDATED`` is allowed.
    """

    def __init__(self):
        self._params: dict[str, dict[str, Any]] = {}
        self._holdouts: dict[str, list[dict[str, Any]]] = {}

    def fit(self, *, parameter_id: str, value, unit: str, target_claim_id: str,
            method: str, run_id: str, bounds=None, uncertainty=None,
            model_discrepancy=None) -> dict:
        rec = {
            'parameter_id': parameter_id, 'value': value, 'unit': unit,
            'origin': 'fitted', 'certainty': 'estimated',
            'target_claim_id': target_claim_id, 'fitting_method': method,
            'parameter_bounds': bounds, 'uncertainty': uncertainty,
            'model_discrepancy': model_discrepancy, 'run_identities': [run_id],
        }
        if parameter_id in self._params:
            for holdout in self._holdouts[parameter_id]:
                holdout['stale_fit'] = True
        self._params[parameter_id] = rec
        self._holdouts.setdefault(parameter_id, [])
        return dict(rec)

    def get(self, parameter_id: str) -> dict:
        return dict(self._params[parameter_id])

    def record_holdout(
        self,
        *,
        parameter_id: str,
        claim_id: str,
        partition: dict,
        frozen_parameter_ids: list,
        frozen_model_revision,
        holdout_run_id: str,
        score: dict,
        evidence_paths: list | None = None,
        used_for_refit: bool = False,
    ) -> dict:
        """Register hold-out evidence. Renaming a claim does not create a hold-out."""
        if parameter_id not in self._params:
            raise KeyError(parameter_id)
        rec = self._params[parameter_id]
        if claim_id == rec['target_claim_id']:
            raise ValueError('hold-out claim_id cannot equal the calibration target_claim_id')
        if not partition:
            raise ValueError('hold-out partition is required')
        if not holdout_run_id:
            raise ValueError('holdout_run_id is required')
        if frozen_model_revision is None:
            raise ValueError('frozen_model_revision is required')
        if not score:
            raise ValueError('hold-out score evidence is required')
        entry = {
            'claim_id': claim_id,
            'partition': deepcopy(partition),
            'frozen_parameter_ids': list(frozen_parameter_ids or []),
            'frozen_model_revision': frozen_model_revision,
            'holdout_run_id': holdout_run_id,
            'score': deepcopy(score),
            'evidence_paths': list(evidence_paths or []),
            'used_for_refit': bool(used_for_refit),
        }
        bucket = self._holdouts.setdefault(parameter_id, [])
        if used_for_refit:
            for prior in bucket:
                if prior.get('claim_id') == claim_id:
                    prior['used_for_refit'] = True
        bucket.append(entry)
        return deepcopy(entry)

    def _qualifying_holdouts(self, parameter_id: str, claim_id: str | None = None) -> list[dict]:
        rec = self._params[parameter_id]
        out: list[dict] = []
        holdouts = self._holdouts.get(parameter_id, [])
        refit_claims = {h['claim_id'] for h in holdouts if h.get('used_for_refit')}
        for holdout in holdouts:
            if holdout.get('stale_fit') or holdout['claim_id'] in refit_claims:
                continue
            if holdout.get('claim_id') == rec['target_claim_id']:
                continue
            if claim_id is not None and holdout.get('claim_id') != claim_id:
                continue
            if not holdout.get('partition') or not holdout.get('holdout_run_id'):
                continue
            if holdout['holdout_run_id'] in rec['run_identities']:
                continue
            if holdout.get('frozen_model_revision') is None or parameter_id not in holdout['frozen_parameter_ids']:
                continue
            scores = holdout['score'].values()
            if not scores or any(not isinstance(score, dict) or score.get('status') != 'PASS' for score in scores):
                continue
            out.append(holdout)
        return out

    def may_independently_validate(self, parameter_id: str, claim_id: str) -> bool:
        """True only with recorded hold-out evidence for a non-target claim."""
        rec = self._params[parameter_id]
        if claim_id == rec['target_claim_id']:
            return False
        return bool(self._qualifying_holdouts(parameter_id, claim_id))

    def final_status(self, parameter_id: str, independent_claim_ids: list[str] | None = None) -> str:
        """Never mint VALIDATED from claim_id names alone."""
        rec = self._params[parameter_id]
        for claim_id in independent_claim_ids or []:
            if claim_id == rec['target_claim_id']:
                continue
            if self._qualifying_holdouts(parameter_id, claim_id):
                return 'VALIDATED'
        return 'CALIBRATED_NOT_INDEPENDENTLY_VALIDATED'
