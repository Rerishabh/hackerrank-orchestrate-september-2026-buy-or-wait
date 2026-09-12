import csv
import re
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from code.schemas.contracts import FinancialEvent, FinancialProfile, PaymentOption, RequestRecord


class DataLoader:
	def __init__(self, dataset_dir: str | Path | None = None):
		self.dataset_dir = Path(dataset_dir) if dataset_dir else Path(__file__).resolve().parents[2] / "dataset"
		self._profiles = self._load_profiles()
		self._requests = self._load_requests()
		self._events_raw = self._read_csv("financial_events.csv")
		self._rates = self._load_rates()
		self._messages = self._read_csv("messages.csv")
		self._images = self._read_csv("images.csv")
		self._options = self._load_options()

	def _read_csv(self, filename: str) -> list[dict[str, str]]:
		with (self.dataset_dir / filename).open(newline="", encoding="utf-8-sig") as handle:
			return list(csv.DictReader(handle))

	@staticmethod
	def _split(value: str | None) -> list[str]:
		return [part.strip() for part in (value or "").split("|") if part.strip()]

	def _load_profiles(self) -> dict[str, FinancialProfile]:
		profiles = {}
		for row in self._read_csv("financial_profiles.csv"):
			row = dict(row)
			for field in ("financial_priorities", "expense_categories_to_protect", "expense_categories_user_is_willing_to_reduce", "expense_categories_user_is_willing_to_stop", "payment_methods_user_will_consider"):
				row[field] = self._split(row.get(field))
			profiles[row["user_id"]] = FinancialProfile.model_validate(row)
		return profiles

	def _load_requests(self) -> dict[str, RequestRecord]:
		return {row["request_id"]: RequestRecord.model_validate(row) for row in self._read_csv("requests.csv")}

	def _load_rates(self) -> dict[tuple[date, str, str], float]:
		return {(date.fromisoformat(row["rate_date"]), row["from_currency"], row["to_currency"]): float(row["rate"]) for row in self._read_csv("exchange_rates.csv")}

	def _load_options(self) -> dict[str, list[PaymentOption]]:
		options: dict[str, list[PaymentOption]] = {}
		for row in self._read_csv("request_payment_options.csv"):
			option = PaymentOption.model_validate(row)
			options.setdefault(option.request_id, []).append(option)
		return options

	def convert_currency(self, amount: float, from_currency: str, to_currency: str, rate_date: date) -> float:
		if from_currency == to_currency:
			return amount
		direct = self._rates.get((rate_date, from_currency, to_currency))
		if direct is not None:
			return amount * direct
		inverse = self._rates.get((rate_date, to_currency, from_currency))
		if inverse is not None:
			return amount / inverse
		for intermediate in {"USD", "EUR", "ZAR", "INR", "IDR"} - {from_currency, to_currency}:
			first = self._rates.get((rate_date, from_currency, intermediate))
			second = self._rates.get((rate_date, intermediate, to_currency))
			if first is not None and second is not None:
				return amount * first * second
		raise ValueError(f"No exchange rate for {from_currency}->{to_currency} on {rate_date}")

	def _amount_from_evidence(self, row: dict[str, str]) -> float | None:
		related_id = row.get("event_id", "")
		texts = [message["message_text"] for message in self._messages if message.get("related_event_id") == related_id]
		numbers = re.findall(r"(?<![A-Za-z])(?:\d[\d ,.]*)", " ".join(texts))
		if not numbers:
			return None
		return float(numbers[-1].replace(",", "").replace(" ", ""))

	def _parse_event(self, row: dict[str, str], profile: FinancialProfile) -> FinancialEvent | None:
		data = dict(row)
		if not data.get("amount"):
			data["amount"] = self._amount_from_evidence(data)
		if data.get("amount") in (None, ""):
			return None
		event = FinancialEvent.model_validate(data)
		settlement = event.settlement_date or event.event_date
		converted = self.convert_currency(event.amount, event.currency, profile.home_currency, settlement)
		return event.model_copy(update={"amount": converted, "currency": profile.home_currency})

	def events_for_user(self, user_id: str, as_of: date | None = None) -> list[FinancialEvent]:
		profile = self._profiles[user_id]
		events = []
		for row in self._events_raw:
			if row.get("user_id") != user_id or row.get("status") in {"failed", "cancelled", "unrealized"}:
				continue
			event = self._parse_event(row, profile)
			if event and (as_of is None or event.event_date <= as_of or (event.settlement_date and event.settlement_date <= as_of)):
				events.append(event)
		return events

	def get_user_context(self, request_id: str) -> dict[str, Any]:
		request = self._requests[request_id]
		profile = self._profiles[request.user_id]
		return {"request": request, "profile": profile, "events": self.events_for_user(request.user_id),
				"payment_options": self._options.get(request_id, []),
				"messages": [m for m in self._messages if m.get("user_id") == request.user_id and (not m.get("request_id") or m.get("request_id") == request_id)],
				"images": [i for i in self._images if i.get("user_id") == request.user_id and (not i.get("request_id") or i.get("request_id") == request_id)]}

	@property
	def requests(self) -> Iterable[RequestRecord]:
		return self._requests.values()
