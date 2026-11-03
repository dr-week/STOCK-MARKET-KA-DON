"""Runs low-resource feedback training after paper outcomes, never in production signals."""

import logging
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from threading import RLock
from typing import Any

from app.feedback import feedback_repository
from app.feedback.feedback_model import _ARTIFACT_DIR, _candidate_path, readiness, train_candidate

logger = logging.getLogger(__name__)


class FeedbackLearningService:
    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="paper-learning")
        self._lock = RLock()
        self._future: Future[dict[str, Any]] | None = None
        self._last_result: dict[str, Any] | None = None

    def schedule_after_outcome(self, provider_id: str | None, db_path: str | None = None) -> None:
        if not provider_id:
            return
        with self._lock:
            if self._future is not None and not self._future.done():
                return
            self._future = self._executor.submit(
                train_candidate, db_path or feedback_repository.DB_PATH, provider_id
            )
            self._future.add_done_callback(self._finish)

    def _finish(self, future: Future[dict[str, Any]]) -> None:
        try:
            result = future.result()
        except Exception:
            logger.exception("Automatic paper-feedback candidate training failed")
            result = {"status": "TRAINING_FAILED"}
        with self._lock:
            self._last_result = result

    def status(self, provider_id: str = "yahoo_finance") -> dict[str, Any]:
        data = readiness(feedback_repository.DB_PATH, provider_id)
        with self._lock:
            running = self._future is not None and not self._future.done()
            last_result = self._last_result
        artifact = _candidate_path(provider_id, _ARTIFACT_DIR)
        saved = last_result if last_result and last_result.get("provider_id") == provider_id else None
        return {
            **data,
            "status": "TRAINING" if running else (
                saved.get("status") if saved else "CANDIDATE_SAVED" if artifact.is_file() else "NOT_READY"
            ),
            "metrics": saved,
            "candidate_saved": artifact.is_file(),
            "production_model_updated": False,
        }


feedback_learning = FeedbackLearningService()
