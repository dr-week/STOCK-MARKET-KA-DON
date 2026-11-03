from collections import Counter
from typing import Any

from sklearn.linear_model import LogisticRegression
from sklearn.metrics import balanced_accuracy_score

from app.ai.training.features import FEATURE_NAMES


def train_time_split(
    samples: list[dict[str, Any]],
    cost_bps: float,
) -> tuple[LogisticRegression, dict[str, Any]]:
    sessions = sorted({sample["session_date"] for sample in samples})
    if len(sessions) < 2:
        raise ValueError("At least two distinct sessions are required for a chronological holdout.")
    test_start = sessions[max(1, int(len(sessions) * 0.8))]
    train = [
        row for row in samples
        if row["session_date"] < test_start and row["label_end_date"] < test_start
    ]
    test = [row for row in samples if row["session_date"] >= test_start]
    if not train or not test or len({row["label"] for row in train}) < 2:
        raise ValueError("The chronological split has insufficient samples or label classes.")

    model = LogisticRegression(class_weight="balanced", max_iter=500, random_state=0)
    model.fit([row["features"] for row in train], [row["label"] for row in train])
    predictions = model.predict([row["features"] for row in test])
    baseline_label = Counter(row["label"] for row in train).most_common(1)[0][0]
    trades = [
        (row, int(prediction))
        for row, prediction in zip(test, predictions)
        if prediction != 0
    ]
    test_labels = [row["label"] for row in test]
    net_returns = [
        (row["forward_return"] * prediction * 10_000) - cost_bps
        for row, prediction in trades
    ]
    metrics = {
        "train_samples": len(train),
        "test_samples": len(test),
        "train_sessions": len({row["session_date"] for row in train}),
        "test_sessions": len({row["session_date"] for row in test}),
        "test_balanced_accuracy": round(
            balanced_accuracy_score(
                test_labels,
                predictions,
            ),
            4,
        ),
        "majority_baseline_balanced_accuracy": round(
            balanced_accuracy_score(test_labels, [baseline_label] * len(test)),
            4,
        ),
        "majority_baseline_accuracy": round(
            sum(label == baseline_label for label in test_labels) / len(test),
            4,
        ),
        "non_neutral_predictions": len(trades),
        "mean_net_bps_per_prediction": round(sum(net_returns) / len(net_returns), 2)
        if net_returns else None,
        "features": FEATURE_NAMES,
        "test_start": test_start,
        "warning": "Per-bar research diagnostic only; overlapping predictions are not a portfolio backtest.",
    }
    return model, metrics
