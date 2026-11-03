from fastapi import APIRouter
from app.feedback.learning_service import feedback_learning
from app.feedback.recorder import feedback_recorder

router = APIRouter()


@router.get("/feedback/accuracy")
def feedback_accuracy():
    """Return overall signal accuracy statistics."""
    return feedback_recorder.get_accuracy_stats()


@router.get("/feedback/calibration")
def feedback_calibration():
    """Return per-signal-type win-rate breakdown."""
    return feedback_recorder.get_signal_calibration()


@router.get("/feedback/learning")
def feedback_learning_status():
    """Report automatic paper-outcome candidate training readiness."""
    return feedback_learning.status()
