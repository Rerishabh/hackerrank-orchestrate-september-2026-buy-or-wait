from collections import defaultdict
from datetime import date, timedelta
import math
from statistics import median
from typing import Iterable

from code.schemas.contracts import FinancialEvent, FinancialProfile


class FinancialSimulator:
	def __init__(
		self,
		profile: FinancialProfile,
		events: Iterable[FinancialEvent],
		request_date: date,
		forecast_days: int = 90,
		stopped_event_ids: Iterable[str] = (),
		reduced_event_amounts: dict[str, float] | None = None,
	):
		self.profile = profile
		self.events = list(events)
		self.request_date = request_date
		self.forecast_days = forecast_days
		self.end_date = request_date + timedelta(days=forecast_days)
		self.stopped_event_ids = set(stopped_event_ids)
		self.reduced_event_amounts = reduced_event_amounts or {}
		self._flows = self._build_flows()

	@staticmethod
	def _next_occurrence(event_date: date, interval: int) -> date:
		if 27 <= interval <= 35:
			month = event_date.month % 12 + 1
			year = event_date.year + (event_date.month // 12)
			day = min(event_date.day, (date(year + (month == 12), month % 12 + 1, 1) - timedelta(days=1)).day)
			return date(year, month, day)
		return event_date + timedelta(days=interval)

	def _build_flows(self) -> dict[date, float]:
		flows: dict[date, float] = defaultdict(float)
		known_dates: set[tuple[str, str, date]] = set()
		grouped: dict[tuple[str, str], list[FinancialEvent]] = defaultdict(list)
		for event in self.events:
			if event.amount is None or not math.isfinite(event.amount):
				continue
			effective_date = event.settlement_date or event.event_date
			known_dates.add((event.category, event.direction, effective_date))
			if event.direction.lower() in {"credit", "in", "income"} and event.status == "pending":
				continue
			if effective_date > self.request_date or (
				effective_date == self.request_date and event.status != "settled"
			):
				flows[effective_date] += self._signed_amount(event)
			if event.status == "settled" and effective_date <= self.request_date:
				grouped[(event.category, event.direction)].append(event)
		for (category, direction), history in grouped.items():
			if len(history) < 2:
				continue
			dates = sorted(event.settlement_date or event.event_date for event in history)
			intervals = [
				(right - left).days
				for left, right in zip(dates, dates[1:])
				if 5 <= (right - left).days <= 370
			]
			if not intervals:
				continue
			interval = max(1, round(median(intervals)))
			representative = max(history, key=lambda event: event.settlement_date or event.event_date)
			forecast_amount = median(event.amount for event in history[-min(len(history), 6):])
			next_date = self._next_occurrence(dates[-1], interval)
			while next_date <= self.end_date:
				if next_date >= self.request_date and (category, direction, next_date) not in known_dates:
					amount = self.reduced_event_amounts.get(representative.event_id, forecast_amount)
					if representative.event_id not in self.stopped_event_ids:
						flows[next_date] += self._signed_amount(representative.model_copy(update={"amount": amount}))
				next_date = self._next_occurrence(next_date, interval)
		return dict(flows)

	@staticmethod
	def _signed_amount(event: FinancialEvent) -> float:
		return event.amount if event.direction.lower() in {"credit", "in", "income"} else -event.amount

	def simulate(self, schedule: Iterable[tuple[date, float]] = ()) -> dict[date, float]:
		additions: dict[date, float] = defaultdict(float)
		for payment_date, amount in schedule:
			additions[payment_date] -= amount
		balance = self.profile.current_available_balance
		balances: dict[date, float] = {}
		for offset in range(self.forecast_days + 1):
			current_date = self.request_date + timedelta(days=offset)
			balance += self._flows.get(current_date, 0.0) + additions.get(current_date, 0.0)
			balances[current_date] = balance
		return balances

	def is_safe(self, schedule: Iterable[tuple[date, float]]) -> bool:
		schedule = list(schedule)
		if any(payment_date < self.request_date or payment_date > self.end_date or amount < 0 for payment_date, amount in schedule):
			return False
		return min(self.simulate(schedule).values()) >= self.profile.minimum_balance_to_keep - 1e-7

	def calculate_amount_safe_to_pay(self, requested_amount: float) -> float:
		headroom_today = max(
			0.0,
			self.profile.current_available_balance - self.profile.minimum_balance_to_keep,
		)
		upper_bound = min(headroom_today, requested_amount)
		if upper_bound <= 0.0:
			return 0.0

		# Validate the amount against every daily balance, including the
		# pre-income trough, without allowing future income to increase today's limit.
		low, high = 0.0, upper_bound
		for _ in range(32):
			candidate = (low + high) / 2
			if self.is_safe(((self.request_date, candidate),)):
				low = candidate
			else:
				high = candidate
		return min(round(low, 2), requested_amount)

	def find_earliest_date_for_full_payment(self, requested_amount: float) -> date | None:
		for offset in range(self.forecast_days + 1):
			candidate = self.request_date + timedelta(days=offset)
			if self.is_safe([(candidate, requested_amount)]):
				return candidate
		return None
