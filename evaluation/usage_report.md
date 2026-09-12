# Evaluation Usage Report

## Summary

- Total requests evaluated: 250
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

- `full_payment`: 63
- `installments`: 58
- `not_recommended`: 59
- `partial_payment`: 10
- `wait`: 60
