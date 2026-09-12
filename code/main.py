import csv
from collections import Counter
from pathlib import Path

from code.engine.loader import DataLoader
from code.engine.planner import PaymentPlanner
from code.engine.simulator import FinancialSimulator


OUTPUT_COLUMNS = [
	"request_id",
	"amount_safe_to_pay",
	"affordability_status",
	"recommended_payment_method",
	"payment_plan",
	"earliest_date_for_full_payment",
	"spending_changes_needed",
	"decision_explanation",
]


def _format_amount(amount: float) -> str:
	return f"{amount:.2f}".rstrip("0").rstrip(".") or "0"


def _write_usage_report(report_path: Path, total_requests: int, distribution: Counter[str]) -> None:
	distribution_lines = "\n".join(
		f"- `{method}`: {count}" for method, count in sorted(distribution.items())
	)
	report_path.parent.mkdir(parents=True, exist_ok=True)
	report_path.write_text(
		"""# Evaluation Usage Report

## Summary

- Total requests evaluated: {total_requests}
- Model provider: none
- Model calls: 0
- Input tokens: 0
- Output tokens: 0
- Estimated total API cost: $0.00
- Estimated average API cost per request: $0.00

## Execution Breakdown

1. Loaded all request, profile, event, exchange-rate, message, image, and payment-option data from `dataset/` with `DataLoader`.
2. Evaluated every request with `PaymentPlanner` and `FinancialSimulator`.
3. Wrote the eight required output columns to the repository-root `output.csv`.
4. Used deterministic local computation only; no external API or token-based service was called.

## Deterministic Rules Applied

- Converted foreign-currency events using the supplied dated exchange rates.
- Excluded failed, cancelled, and unrealized events from cash-flow projections.
- Reserved the configured minimum balance and forecasted known and recurring flows over the simulator horizon.
- Considered full payment, permitted partial payment, accepted installment options, waiting, and not-recommended outcomes.
- Enforced payment preferences, installment limits, completion deadlines, and minimum-balance safety for each candidate plan.

## Recommended Payment Method Distribution

{distribution_lines}
""".format(total_requests=total_requests, distribution_lines=distribution_lines),
		encoding="utf-8",
	)


def main() -> None:
	repository_root = Path(__file__).resolve().parents[1]
	loader = DataLoader(repository_root / "dataset")
	planner = PaymentPlanner(loader, FinancialSimulator)
	rows = []
	distribution: Counter[str] = Counter()

	for request in loader.requests:
		record = planner.evaluate_request(request.request_id)
		row = record.model_dump(mode="json")
		row["amount_safe_to_pay"] = _format_amount(record.amount_safe_to_pay)
		rows.append(row)
		distribution[record.recommended_payment_method.value] += 1

	output_path = repository_root / "output.csv"
	with output_path.open("w", newline="", encoding="utf-8") as handle:
		writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS)
		writer.writeheader()
		writer.writerows(rows)

	_write_usage_report(repository_root / "evaluation" / "usage_report.md", len(rows), distribution)

	print(f"Processed rows: {len(rows)}")
	print("Recommended payment method distribution:")
	for method, count in sorted(distribution.items()):
		print(f"  {method}: {count}")


if __name__ == "__main__":
	main()
