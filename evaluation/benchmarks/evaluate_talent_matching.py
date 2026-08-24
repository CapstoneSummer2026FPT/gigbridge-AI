"""Evaluate human-reviewed talent-match runs stored as JSON Lines."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from pathlib import Path


def recall_at(ranked: list[str], relevant: set[str], k: int) -> float:
    if not relevant:
        return 1.0
    return len(set(ranked[:k]) & relevant) / len(relevant)


def ndcg_at(ranked: list[str], grades: dict[str, int], k: int) -> float:
    def dcg(items: list[str]) -> float:
        return sum(
            (2 ** grades.get(candidate_id, 0) - 1) / math.log2(index + 2)
            for index, candidate_id in enumerate(items[:k])
        )

    ideal = sorted(grades, key=lambda candidate_id: grades[candidate_id], reverse=True)
    ideal_score = dcg(ideal)
    return dcg(ranked) / ideal_score if ideal_score else 1.0


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * fraction) - 1)
    return ordered[index]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", type=Path)
    parser.add_argument("--allow-small-sample", action="store_true")
    args = parser.parse_args()

    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(rows) < 100 and not args.allow_small_sample:
        print(f"Evaluation requires at least 100 human-reviewed pairs; found {len(rows)}.")
        return 2

    recalls: list[float] = []
    ndcgs: list[float] = []
    latencies: list[float] = []
    invalid_ids = 0
    for row in rows:
        ranked = row["ranked_freelancer_ids"]
        eligible = set(row["eligible_freelancer_ids"])
        relevant = set(row["relevant_freelancer_ids"])
        grades = {key: int(value) for key, value in row["relevance_grades"].items()}
        invalid_ids += sum(candidate_id not in eligible for candidate_id in ranked)
        recalls.append(recall_at(ranked, relevant, 20))
        ndcgs.append(ndcg_at(ranked, grades, 10))
        latencies.append(float(row["latency_ms"]))

    metrics = {
        "pair_count": len(rows),
        "recall_at_20": round(statistics.fmean(recalls), 4),
        "ndcg_at_10": round(statistics.fmean(ndcgs), 4),
        "invalid_candidate_ids": invalid_ids,
        "p95_latency_ms": round(percentile(latencies, 0.95), 2),
    }
    print(json.dumps(metrics, indent=2))
    passed = (
        metrics["recall_at_20"] >= 0.85
        and metrics["ndcg_at_10"] >= 0.70
        and metrics["invalid_candidate_ids"] == 0
        and metrics["p95_latency_ms"] < 15_000
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
