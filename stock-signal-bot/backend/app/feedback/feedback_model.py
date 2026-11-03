"""Outcome-driven, provider-isolated paper-trade candidate training."""

import json
import math
import re
import sqlite3
from collections import Counter
from contextlib import closing
from datetime import datetime, time, timezone
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score

from app.feedback import feedback_repository
from app.feedback.feedback_features import FEATURE_NAMES
from app.storage_paths import RESEARCH_DIR

MIN_OUTCOMES = 100
MIN_DIRECTIONAL_CLASS = 20
MIN_SESSIONS = 30
_IST = ZoneInfo("Asia/Kolkata")
_ARTIFACT_DIR = RESEARCH_DIR


def _session_date(timestamp: str) -> str:
    parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return parsed.astimezone(_IST).date().isoformat()


def _load_rows(db_path: str, provider_id: str) -> list[dict[str, Any]]:
    uri = f"{Path(db_path).resolve().as_uri()}?mode=ro"
    with closing(sqlite3.connect(uri, uri=True)) as connection:
        rows = connection.execute(
            """SELECT features_json, outcome, signal_at, outcome_at
               FROM signal_outcomes
               WHERE provider_id=? AND outcome IN ('WIN', 'LOSS')
                 AND features_json IS NOT NULL AND outcome_at IS NOT NULL
               ORDER BY signal_at""",
            (provider_id,),
        ).fetchall()
    samples = []
    for raw_features, outcome, signal_at, outcome_at in rows:
        try:
            features = json.loads(raw_features)
            vector = [float(features[name]) for name in FEATURE_NAMES]
            if not all(math.isfinite(value) for value in vector):
                continue
            sample = {
                "features": vector,
                "label": 1 if outcome == "WIN" else 0,
                "signal_at": signal_at,
                "outcome_at": outcome_at,
                "session": _session_date(signal_at),
            }
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
        samples.append(sample)
    return samples


def readiness(db_path: str, provider_id: str) -> dict[str, Any]:
    samples = _load_rows(db_path, provider_id)
    counts = Counter(sample["label"] for sample in samples)
    sessions = len({sample["session"] for sample in samples})
    ready = (
        len(samples) >= MIN_OUTCOMES
        and counts[1] >= MIN_DIRECTIONAL_CLASS
        and counts[0] >= MIN_DIRECTIONAL_CLASS
        and sessions >= MIN_SESSIONS
    )
    return {
        "provider_id": provider_id,
        "eligible_outcomes": len(samples),
        "wins": counts[1],
        "losses": counts[0],
        "sessions": sessions,
        "required_outcomes": MIN_OUTCOMES,
        "required_each_class": MIN_DIRECTIONAL_CLASS,
        "required_sessions": MIN_SESSIONS,
        "ready": ready,
    }


def _candidate_path(provider_id: str, output_dir: Path) -> Path:
    safe_provider = re.sub(r"[^A-Za-z0-9._-]", "_", provider_id)
    return output_dir / f"paper_candidate_{safe_provider}.joblib"


def train_candidate(
    db_path: str = feedback_repository.DB_PATH,
    provider_id: str = "yahoo_finance",
    output_dir: Path = _ARTIFACT_DIR,
) -> dict[str, Any]:
    samples = _load_rows(db_path, provider_id)
    status = readiness(db_path, provider_id)
    if not status["ready"]:
        return {"status": "NOT_READY", **status}

    sessions = sorted({sample["session"] for sample in samples})
    split_day = sessions[max(1, int(len(sessions) * 0.8))]
    split_at = datetime.combine(
        datetime.fromisoformat(split_day).date(), time.min, tzinfo=_IST
    ).astimezone(timezone.utc)
    train = [
        row for row in samples
        if row["session"] < split_day
        and datetime.fromisoformat(row["outcome_at"].replace("Z", "+00:00")) < split_at
    ]
    test = [row for row in samples if row["session"] >= split_day]
    if len({row["label"] for row in train}) != 2 or not test:
        return {"status": "NOT_READY", **status, "reason": "Chronological split lacks both training classes or test rows."}

    model = LogisticRegression(class_weight="balanced", max_iter=500, random_state=0)
    model.fit([row["features"] for row in train], [row["label"] for row in train])
    predictions = model.predict([row["features"] for row in test])
    majority = Counter(row["label"] for row in train).most_common(1)[0][0]
    score = balanced_accuracy_score([row["label"] for row in test], predictions)
    baseline = balanced_accuracy_score(
        [row["label"] for row in test], [majority] * len(test)
    )
    metrics = {
        **status,
        "status": "CANDIDATE_READY_FOR_REVIEW" if score > baseline else "CANDIDATE_BELOW_BASELINE",
        "train_samples": len(train),
        "test_samples": len(test),
        "test_start_session": split_day,
        "balanced_accuracy": round(float(score), 4),
        "majority_baseline_balanced_accuracy": round(float(baseline), 4),
        "features": FEATURE_NAMES,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "provider_id": provider_id,
        "promotion": "manual only; candidate is never loaded by production signals",
        "warning": "Paper outcomes are gross of costs and are not an execution-accurate live dataset.",
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    artifact = _candidate_path(provider_id, output_dir)
    temporary = artifact.with_suffix(".tmp")
    joblib.dump({"model": model, "metrics": metrics}, temporary)
    temporary.replace(artifact)
    return {**metrics, "artifact": str(artifact)}
