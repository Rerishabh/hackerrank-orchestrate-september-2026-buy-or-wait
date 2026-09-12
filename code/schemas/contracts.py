from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AffordabilityStatus(str, Enum):
	AFFORDABLE_NOW = "affordable_now"
	AFFORDABLE_WITH_PLAN = "affordable_with_plan"
	AFFORDABLE_LATER = "affordable_later"
	NOT_AFFORDABLE = "not_affordable"


class PaymentMethod(str, Enum):
	FULL_PAYMENT = "full_payment"
	PARTIAL_PAYMENT = "partial_payment"
	INSTALLMENTS = "installments"
	WAIT = "wait"
	NOT_RECOMMENDED = "not_recommended"


class RequestType(str, Enum):
	PURCHASE = "purchase"
	TRAVEL = "travel"
	EDUCATION = "education"
	FAMILY_TRANSFER = "family_transfer"
	DEBT_REPAYMENT = "debt_repayment"
	INVESTMENT = "investment"
	HOUSING = "housing"
	EMERGENCY_EXPENSE = "emergency_expense"
	OTHER = "other"


class ContractModel(BaseModel):
	model_config = ConfigDict(extra="ignore", populate_by_name=True)


class FinancialProfile(ContractModel):
	user_id: str
	home_currency: str
	current_available_balance: float
	minimum_balance_to_keep: float
	financial_priorities: list[str] = Field(default_factory=list)
	expense_categories_to_protect: list[str] = Field(default_factory=list)
	expense_categories_user_is_willing_to_reduce: list[str] = Field(default_factory=list)
	expense_categories_user_is_willing_to_stop: list[str] = Field(default_factory=list)
	payment_methods_user_will_consider: list[PaymentMethod] = Field(default_factory=list)
	max_installment_months: Optional[int] = None

	@field_validator("max_installment_months", mode="before")
	@classmethod
	def blank_months_to_none(cls, value):
		return None if value in (None, "") else int(value)


class FinancialEvent(ContractModel):
	event_id: str
	user_id: str
	event_type: str
	description: str = ""
	category: str = "other"
	direction: str
	amount: Optional[float] = None
	currency: str
	event_date: date
	settlement_date: Optional[date] = None
	status: str
	linked_event_id: Optional[str] = None
	flexibility: str = "fixed"
	minimum_allowed_amount: Optional[float] = None

	@field_validator("amount", "minimum_allowed_amount", mode="before")
	@classmethod
	def blank_amount_to_none(cls, value):
		return None if value in (None, "") else float(value)


class PaymentOption(ContractModel):
	payment_option_id: str
	request_id: str
	payment_method: PaymentMethod
	payment_amount: float
	number_of_payments: int
	first_payment_date: date
	payment_frequency_days: Optional[int] = None
	financing_fee: float = 0.0
	total_payable_amount: float

	@field_validator("payment_frequency_days", mode="before")
	@classmethod
	def blank_frequency_to_none(cls, value):
		return None if value in (None, "") else int(value)


class RequestRecord(ContractModel):
	request_id: str
	user_id: str
	request_date: date
	request_type: RequestType
	requested_amount: float
	desired_completion_date: date
	allows_partial_payment: bool
	request_text: str = ""

	@field_validator("allows_partial_payment", mode="before")
	@classmethod
	def parse_bool(cls, value):
		if isinstance(value, bool):
			return value
		return str(value).strip().lower() in {"true", "1", "yes", "y"}


class OutputRecord(ContractModel):
	request_id: str
	amount_safe_to_pay: float
	affordability_status: AffordabilityStatus
	recommended_payment_method: PaymentMethod
	payment_plan: str
	earliest_date_for_full_payment: Optional[date] = None
	spending_changes_needed: str = "none"
	decision_explanation: str
