from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
if str(REPOSITORY_ROOT) not in sys.path:
	sys.path.insert(0, str(REPOSITORY_ROOT))

from code.engine.loader import DataLoader
from code.engine.planner import PaymentPlanner
from code.engine.simulator import FinancialSimulator
from code.schemas.contracts import RequestRecord


FIELDS = (
	"amount_safe_to_pay",
	"affordability_status",
	"recommended_payment_method",
	"payment_plan",
	"earliest_date_for_full_payment",
)


def _inject_missing_requests(loader: DataLoader, samples: pd.DataFrame) -> None:
	request_ids = {str(request_id) for request_id in loader.requests}
	missing = samples[~samples["request_id"].astype(str).isin(request_ids)]
	if missing.empty:
		return

	for row in missing.to_dict(orient="records"):
		request = RequestRecord.model_validate(row)
		loader._requests[request.request_id] = request


def _normalized_date(value: object) -> str:
	if value is None or pd.isna(value):
		return ""
	return value.isoformat() if hasattr(value, "isoformat") else str(value).strip()


def _predicted_value(record: object, field: str) -> object:
	value = getattr(record, field)
	if field == "amount_safe_to_pay":
		return float(value)
	if field in {"affordability_status", "recommended_payment_method"}:
		return value.value
	if field == "earliest_date_for_full_payment":
		return _normalized_date(value)
	return value


def _expected_value(row: pd.Series, field: str) -> object:
	value = row[field]
	if field == "amount_safe_to_pay":
		return float(value)
	if field == "earliest_date_for_full_payment":
		return _normalized_date(value)
	return str(value).strip()


def _matches(field: str, predicted: object, expected: object) -> bool:
	if field == "amount_safe_to_pay":
		return abs(float(predicted) - float(expected)) <= 1.0
	return predicted == expected


def run_sample_eval() -> None:
	samples_path = REPOSITORY_ROOT / "dataset" / "sample_requests.csv"
	samples = pd.read_csv(samples_path)
	loader = DataLoader("dataset")
	_inject_missing_requests(loader, samples)
	planner = PaymentPlanner(loader, FinancialSimulator)

	matches = {field: 0 for field in FIELDS}
	mismatches: list[tuple[str, dict[str, object], dict[str, object]]] = []

	for _, row in samples.iterrows():
		request_id = str(row["request_id"]).strip()
		prediction = planner.evaluate_request(request_id)
		predicted = {field: _predicted_value(prediction, field) for field in FIELDS}
		expected = {field: _expected_value(row, field) for field in FIELDS}

		field_matches = {
			field: _matches(field, predicted[field], expected[field])
			for field in FIELDS
		}
		for field, matched in field_matches.items():
			if matched:
				matches[field] += 1
		if not all(field_matches.values()):
			mismatches.append((request_id, predicted, expected))

	total = len(samples)
	print(f"--- SAMPLE BENCHMARK RESULTS ({total} SAMPLES) ---")
	print(f"Total sample count: {total}")
	print("\nField accuracy:")
	for field in FIELDS:
		count = matches[field]
		print(f"- {field}: {count}/{total} ({count / total * 100:.1f}%)")

	print(f"\nMismatched request IDs: {len(mismatches)}")
	if mismatches:
		for request_id, predicted, expected in mismatches:
			print(f"[{request_id}]")
			print(f"  Predicted: {predicted}")
			print(f"  Expected:  {expected}")
	else:
		print("None")


if __name__ == "__main__":
	run_sample_eval()
