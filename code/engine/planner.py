from dataclasses import dataclass
from datetime import date, timedelta
from itertools import combinations
from typing import Iterable

from code.engine.loader import DataLoader
from code.engine.simulator import FinancialSimulator
from code.schemas.contracts import (
	AffordabilityStatus,
	OutputRecord,
	PaymentMethod,
	PaymentOption,
)


@dataclass(frozen=True)
class _Candidate:
	method: PaymentMethod
	schedule: tuple[tuple[date, float], ...]
	total_amount: float
	completes_by_deadline: bool
	payment_option_id: str = ""
	spending_changes: str = "none"

	@property
	def start_date(self) -> date:
		return self.schedule[0][0] if self.schedule else date.max

	@property
	def sort_key(self) -> tuple[bool, bool, int, float, int, date, int, str]:
		return (
			not self.completes_by_deadline,
			self.spending_changes != "none",
			0 if self.spending_changes == "none" else len(self.spending_changes.split("|")),
			self.total_amount,
			0 if self.method is PaymentMethod.PARTIAL_PAYMENT else 1,
			self.start_date,
			len(self.schedule),
			self.payment_option_id,
		)


class PaymentPlanner:
	def __init__(self, loader: DataLoader, simulator_cls: type[FinancialSimulator]):
		self.loader = loader
		self.simulator_cls = simulator_cls

	@staticmethod
	def _format_amount(amount: float) -> str:
		return f"{amount:.2f}" if amount % 1 else str(int(amount))

	@classmethod
	def _format_schedule(cls, schedule: Iterable[tuple[date, float]]) -> str:
		return "|".join(f"{payment_date.isoformat()}:{cls._format_amount(amount)}" for payment_date, amount in schedule)

	def _installment_schedule(self, option: PaymentOption) -> tuple[tuple[date, float], ...]:
		frequency = option.payment_frequency_days or 0
		return tuple(
			(
				option.first_payment_date + timedelta(days=frequency * index),
				option.payment_amount,
			)
			for index in range(option.number_of_payments)
		)

	def _spending_change_options(self, context: dict) -> list[tuple[tuple[str, ...], dict[str, float]]]:
		request = context["request"]
		profile = context["profile"]
		latest: dict[tuple[str, str, str], object] = {}
		for event in context["events"]:
			if event.event_date <= request.request_date and event.flexibility != "fixed":
				key = (event.category, event.direction, event.description)
				if key not in latest or event.event_date > latest[key].event_date:
					latest[key] = event

		options: list[tuple[str, str, object, float | None]] = []
		for event in latest.values():
			if event.flexibility == "stoppable" and event.category in profile.expense_categories_user_is_willing_to_stop:
				options.append((f"stop:{event.event_id}", "stop", event, None))
			elif event.flexibility in {"reducible", "reducible_or_stoppable"} and event.category in profile.expense_categories_user_is_willing_to_reduce:
				amount = event.minimum_allowed_amount
				if amount is not None and amount < event.amount:
					options.append((f"reduce_to:{event.event_id}:{self._format_amount(amount)}", "reduce", event, amount))

		changes = [((), {})]
		for size in range(1, min(3, len(options)) + 1):
			for selected in combinations(options, size):
				if any(item[1] == "stop" and other[1] == "reduce" and item[2].event_id == other[2].event_id for item in selected for other in selected):
					continue
				changes.append((tuple(item[0] for item in selected), {item[2].event_id: item[3] for item in selected if item[3] is not None}))
		return changes

	@staticmethod
	def _status_for(method: PaymentMethod) -> AffordabilityStatus:
		if method is PaymentMethod.FULL_PAYMENT:
			return AffordabilityStatus.AFFORDABLE_NOW
		if method in {PaymentMethod.PARTIAL_PAYMENT, PaymentMethod.INSTALLMENTS}:
			return AffordabilityStatus.AFFORDABLE_WITH_PLAN
		if method is PaymentMethod.WAIT:
			return AffordabilityStatus.AFFORDABLE_LATER
		return AffordabilityStatus.NOT_AFFORDABLE

	def evaluate_request(self, request_id: str) -> OutputRecord:
		context = self.loader.get_user_context(request_id)
		request = context["request"]
		profile = context["profile"]
		base_simulator = self.simulator_cls(profile, context["events"], request.request_date)
		safe_today = min(request.requested_amount, max(0.0, base_simulator.calculate_amount_safe_to_pay(request.requested_amount)))
		safe_today = round(safe_today, 2)
		baseline_earliest = base_simulator.find_earliest_date_for_full_payment(request.requested_amount)
		accepted = set(profile.payment_methods_user_will_consider)
		if (
			PaymentMethod.FULL_PAYMENT in accepted
			and safe_today >= request.requested_amount
			and base_simulator.is_safe(((request.request_date, request.requested_amount),))
		):
			return OutputRecord.model_validate(
				{
					"request_id": request.request_id,
					"amount_safe_to_pay": safe_today,
					"affordability_status": AffordabilityStatus.AFFORDABLE_NOW,
					"recommended_payment_method": PaymentMethod.FULL_PAYMENT,
					"payment_plan": self._format_schedule(((request.request_date, request.requested_amount),)),
					"earliest_date_for_full_payment": request.request_date,
					"spending_changes_needed": "none",
					"decision_explanation": f"Pay {profile.home_currency} {self._format_amount(request.requested_amount)} today while maintaining the minimum balance.",
				},
				context={"requested_amount": request.requested_amount},
			)
		candidates: list[_Candidate] = []

		for change_ids, reductions in self._spending_change_options(context):
			simulator = self.simulator_cls(profile, context["events"], request.request_date, stopped_event_ids=[item.split(":", 1)[1] for item in change_ids if item.startswith("stop:")], reduced_event_amounts=reductions)
			earliest = baseline_earliest
			changes = "|".join(change_ids) or "none"
			if PaymentMethod.FULL_PAYMENT in accepted and safe_today >= request.requested_amount and simulator.is_safe(((request.request_date, request.requested_amount),)):
				candidates.append(_Candidate(PaymentMethod.FULL_PAYMENT, ((request.request_date, request.requested_amount),), request.requested_amount, True, spending_changes=changes))

			if (
				PaymentMethod.PARTIAL_PAYMENT in accepted
				and request.allows_partial_payment
				and 0 < safe_today < request.requested_amount
				and earliest is not None
			):
				second_payment = round(request.requested_amount - safe_today, 2)
				schedule = ((request.request_date, safe_today), (earliest, second_payment))
				if earliest <= request.desired_completion_date and simulator.is_safe(schedule):
					candidates.append(
						_Candidate(
							PaymentMethod.PARTIAL_PAYMENT,
							schedule,
							request.requested_amount,
							True,
							spending_changes=changes,
						)
					)

			if PaymentMethod.INSTALLMENTS in accepted:
				for option in sorted(context["payment_options"], key=lambda item: item.payment_option_id):
					if option.payment_method is not PaymentMethod.INSTALLMENTS:
						continue
					if profile.max_installment_months is not None and option.number_of_payments > profile.max_installment_months:
						continue
					frequency_days = option.payment_frequency_days or 0
					final_payment_date = option.first_payment_date + timedelta(
						days=(option.number_of_payments - 1) * frequency_days
					)
					if final_payment_date > request.desired_completion_date:
						continue
					schedule = self._installment_schedule(option)
					if not schedule:
						continue
					if simulator.is_safe(schedule):
						candidates.append(_Candidate(PaymentMethod.INSTALLMENTS, schedule, option.total_payable_amount, True, option.payment_option_id, changes))

			if not change_ids and PaymentMethod.FULL_PAYMENT in accepted and earliest is not None:
				wait_schedule = ((earliest, request.requested_amount),)
				if simulator.is_safe(wait_schedule):
					candidates.append(_Candidate(PaymentMethod.WAIT, wait_schedule, request.requested_amount, earliest <= request.desired_completion_date, spending_changes=changes))

		earliest = baseline_earliest

		if not candidates:
			return OutputRecord.model_validate(
				{
					"request_id": request.request_id,
					"amount_safe_to_pay": safe_today,
					"affordability_status": AffordabilityStatus.NOT_AFFORDABLE,
					"recommended_payment_method": PaymentMethod.NOT_RECOMMENDED,
					"payment_plan": "none",
					"earliest_date_for_full_payment": earliest,
					"spending_changes_needed": "none",
					"decision_explanation": f"Do not proceed. Only {profile.home_currency} {self._format_amount(safe_today)} is safe today while protecting the minimum balance.",
				},
				context={"requested_amount": request.requested_amount},
			)

		candidate = min(candidates, key=lambda item: item.sort_key)
		full_date = candidate.schedule[-1][0]
		if candidate.method is PaymentMethod.FULL_PAYMENT:
			explanation = f"Pay {profile.home_currency} {self._format_amount(request.requested_amount)} today while maintaining the minimum balance."
		elif candidate.method is PaymentMethod.WAIT:
			explanation = f"Wait until {full_date.isoformat()}, when the full payment is forecast safe above the minimum balance."
		elif candidate.method is PaymentMethod.INSTALLMENTS:
			explanation = f"Use {len(candidate.schedule)} installments totaling {profile.home_currency} {self._format_amount(candidate.total_amount)} while maintaining the minimum balance."
		else:
			explanation = f"Pay {profile.home_currency} {self._format_amount(safe_today)} today and the remainder on {full_date.isoformat()} while maintaining the minimum balance."
		return OutputRecord.model_validate(
			{
				"request_id": request.request_id,
				"amount_safe_to_pay": safe_today,
				"affordability_status": (
					AffordabilityStatus.AFFORDABLE_WITH_PLAN
					if candidate.spending_changes != "none"
					else self._status_for(candidate.method)
				),
				"recommended_payment_method": candidate.method,
				"payment_plan": self._format_schedule(candidate.schedule),
				"earliest_date_for_full_payment": earliest,
				"spending_changes_needed": candidate.spending_changes,
				"decision_explanation": explanation,
			},
			context={"requested_amount": request.requested_amount},
		)
