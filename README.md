# HackerRank Orchestrate September 2026: Buy or Wait?

[![Python](https://img.shields.io/badge/Python-3.x-blue?logo=python)](https://www.python.org/)
[![HackerRank](https://img.shields.io/badge/HackerRank-Orchestrate-green)](https://www.hackerrank.com/hackerrank-orchestrate-september26)

> Financial affordability decision engine built for the HackerRank Orchestrate September 2026 24-hour hackathon. The system reconstructs a user's financial state, forecasts future cash flow, evaluates payment options, and produces a structured affordability decision.

## Overview

A simple question such as:

> **"Can I afford this laptop?"**

requires more than checking the user's current bank balance.

A reliable affordability decision can depend on:

- Current available balance
- Minimum preferred balance
- Recurring expenses
- Pending transactions
- Confirmed income
- Future financial commitments
- Essential spending
- Payment and installment options
- User preferences
- Supporting information in messages
- Financial evidence in images

The system combines these financial factors to produce a structured affordability decision.

### Decision Categories

**Affordability Status**

- `affordable_now`
- `affordable_with_plan`
- `affordable_later`
- `not_affordable`

**Recommended Payment Method**

- `full_payment`
- `partial_payment`
- `installments`
- `wait`
- `not_recommended`

## Challenge

This project was developed for **HackerRank Orchestrate September 2026**, a 24-hour hackathon focused on designing, building, and shipping an AI agent.

The challenge started on **September 12, 2026 at 6:00 PM IST**. HackerRank describes Orchestrate as a challenge where participants submit their code, agent output, and AI chat transcript, followed by an AI Judge interview. 

### Official Challenge

[HackerRank Orchestrate September 2026](https://www.hackerrank.com/hackerrank-orchestrate-september26)

### My Leaderboard Result

[View My Buy or Wait Leaderboard Result](https://www.hackerrank.com/contests/hackerrank-orchestrate-september26/challenges/buy-or-wait/leaderboard?username=ap24110010666)

## Approach

The submitted solution treats affordability as a **financial forecasting problem** across a 90-day horizon rather than as a static day-0 balance check.

```text
User Request
     │
     ▼
Financial Context
     ├── Financial Profile
     ├── Financial Events
     ├── Recurring Expenses
     ├── Pending Transactions
     ├── Confirmed Income
     ├── Messages
     ├── Supporting Evidence
     └── Payment Options
     │
     ▼
Financial State Reconstruction
     │
     ▼
Future Cash-Flow Forecast
     │
     ▼
Affordability Calculation
     │
     ▼
Payment Plan / Spending Change Analysis
     │
     ▼
Deterministic Validation
     │
     ▼
Structured Output
```
Key Decision Logic

1. Reconstruct the Financial State

The system aggregates available financial information for each user, including current balance, minimum balance thresholds, recurring commitments, pending transactions, confirmed income, and user preferences.


2. Forecast Future Cash Flow

Affordability is evaluated across the forecast horizon. The system checks whether the projected balance remains above the required minimum balance.


3. Protect Essential Spending

A purchase is not considered safe simply because sufficient funds exist today. Required financial commitments and essential recurring expenses must be considered before approving a purchase.


4. Evaluate Payment Options

When full payment is not immediately safe, the system evaluates alternatives such as partial payment, installment schedules, or delayed execution.


5. Evaluate Flexible Spending Changes

When permitted flexible recurring expenses exist, the system can consider changes such as:

stop:<event_id>

reduce_to:<event_id>:<amount>


These changes can alter the future cash-flow trajectory and therefore affect affordability.


6. Validate the Final Decision

A deterministic validation layer checks output constraints including amount bounds, payment schedules, date consistency, and output schema compliance.



Output Format

The primary generated file is output.csv.

Each request produces one structured prediction row.

Required Columns

Column	Description

request_id	Unique identifier of the request
amount_safe_to_pay	Maximum amount that can safely be paid on the request date
affordability_status	Overall affordability classification
recommended_payment_method	Recommended payment approach
payment_plan	Chronological payment schedule
earliest_date_for_full_payment	Earliest forecast date on which full payment is safe
spending_changes_needed	Permitted changes to flexible recurring expenses
decision_explanation	Explanation of the decision and relevant financial factors


Partial Payment Logic

When partial payment is permitted and safe, the payment schedule contains exactly two payments formatted as:

request_date:amount|earliest_date:amount

Example:

2026-09-12:5000|2026-09-25:7000

Repository Structure

.
├── code/
│   ├── main.py
│   ├── engine/
│   └── evaluation/
├── evaluation/
│   └── usage_report.md
├── AGENTS.md
├── CLAUDE.md
├── README.md
├── problem_statement.md
├── output.csv
└── .gitignore

code/: Implementation of the financial decision engine, simulation pipeline, and execution scripts.

evaluation/usage_report.md: Model call counts, token usage, and execution cost documentation.

problem_statement.md: Challenge specification reference.

output.csv: Generated predictions produced by the engine.

AGENTS.md and CLAUDE.md: AI-assisted development instructions and project guidelines.


Dataset

The original HackerRank challenge dataset is not included in this public repository.

The challenge data contained financial profiles, transaction histories, requests, sample data, and supporting media.

Raw dataset assets are maintained separately in a private backup repository for preservation purposes.

This public repository contains the project implementation, documentation, evaluation reports, and generated output.

Running the Project

The solution expects the challenge dataset to be available locally in a dataset/ directory.

With the dataset available locally, run:

python code/main.py

Predictions will be written to:

output.csv

Environment Setup

Create a virtual environment:

python -m venv .venv

Windows

.venv\Scripts\activate

macOS/Linux

source .venv/bin/activate

Install the project's required dependencies according to its Python configuration, then run:

python code/main.py

Evaluation & Results

The project was submitted to HackerRank Orchestrate September 2026.

The final submission was evaluated across the submitted code, generated output, AI chat transcript, and AI Judge interview. HackerRank describes these as separate signals used to evaluate Orchestrate submissions.

Final Leaderboard Result

Metric	Result

Final Rank	#1504 / 3,062
Total Score	40.6 / 100


View the HackerRank Leaderboard

Score Breakdown

Component	Score	Max Possible

Chat Transcript	6.4	10
AI Judge Interview	18.9	30
Output CSV	12.3	30
Code ZIP	3.0	30


Detailed execution metrics and model usage are available in evaluation/usage_report.md.

HackerRank Post-Submission Feedback

HackerRank provided detailed feedback after evaluating the submission.

The main architectural feedback was that the submitted implementation was primarily a deterministic solver, rather than a model-driven agent.

HackerRank recommended keeping the existing deterministic loader, planner, and simulator as tools, while adding an agent loop capable of:

1. Extracting evidence from messages and images.


2. Deciding what action to take under uncertainty.


3. Proposing candidate plans.


4. Calling deterministic simulation tools to verify minimum-balance safety.


5. Validating the final structured output before writing the CSV.



The recommended architecture can therefore be summarized as:

Financial Inputs
       │
       ▼
   AI Agent
       │
       ├── Evidence Extraction
       │
       ├── Decision Making
       │
       ├── Candidate Plan
       │
       ▼
Deterministic Tools
       │
       ├── Financial State Loader
       ├── Planner
       └── Cash-Flow Simulator
       │
       ▼
Safety Validation
       │
       ▼
Consistent Structured Output

Key Feedback Themes

1. Model-Driven Decision Making

The submitted workflow relied primarily on predefined planning and simulation logic. A future version should allow the model to select actions and invoke deterministic tools rather than only executing a fixed workflow.

2. Evidence Extraction

A future agent should be able to extract relevant evidence from messy inputs such as messages and images using dedicated tools.

3. Output Consistency

The amount_safe_to_pay, affordability_status, payment_plan, earliest_date_for_full_payment, spending_changes_needed, and decision_explanation fields should all be derived from the same underlying validated plan.

4. Flexible Expense Modeling

Stop/reduce changes to flexible expenses should be modeled directly inside the financial forecast. The forecast should then be recomputed before determining the safe-to-pay amount and final status.

5. Safety Under Uncertainty

The system should explicitly define how missing or uncertain evidence is handled, including when assumptions are allowed and when the system should return an insufficient-evidence outcome.

6. Reliability

A future implementation should validate inputs early, validate model output structure, use bounded retries and fallbacks, and ensure that one failed request does not break the entire run.

Engineering Takeaways

Financial Decisions Require Forecasting: Current balance alone is insufficient when future income, pending transactions, recurring expenses, and minimum-balance requirements affect liquidity.

Deterministic Tools and AI Agents Can Complement Each Other: Deterministic simulation is useful for enforcing financial constraints, while an agent can handle evidence extraction, uncertainty, tool selection, and candidate-plan generation.

One Plan Should Drive the Final Output: Payment amounts, status, dates, spending changes, and explanations should all agree with the same underlying simulation result.

Validation Should Be a Separate Safety Layer: Model-generated decisions should pass deterministic checks before reaching the final output.

Explicit Specifications Improve AI-Assisted Development: Defining formulas, thresholds, invariants, tie-break rules, expected behavior, and failing cases before implementation reduces ambiguity during AI-assisted coding.

Concrete Debugging Evidence Matters: Providing exact failing request IDs, incorrect fields, expected behavior, and observed output makes debugging more precise.


Limitations

The project was developed under a 24-hour hackathon constraint.

The original challenge dataset is not included in this public repository.

The submitted September 2026 implementation primarily uses deterministic planning and simulation rather than a fully model-driven agent loop.

The system was designed for the challenge environment and has not been validated for real-world financial applications.

Financial decisions can depend on information that is unavailable, incomplete, delayed, or incorrectly represented in the available data.


Future Improvements

Based on the post-submission feedback, a future version could introduce:

Model-driven agent orchestration

Dedicated evidence extraction tools

Tool selection and tool-calling by the agent

Candidate-plan generation by the model

Deterministic simulation as a verification tool

Explicit uncertainty and fallback policies

Improved stop/reduce expense modeling

End-to-end output consistency validation

Stronger error handling and bounded retries

More comprehensive regression tests

Concrete monitoring signals and production tripwires


The intended architecture would be:

Model proposes
      ↓
Deterministic tools verify
      ↓
Validator enforces
      ↓
Structured output

Disclaimer

This project was developed as a hackathon submission for educational and demonstration purposes.

It is not a financial advisory tool and should not be used for real-world financial decision-making.

Author

Rishabh Paira

GitHub: @Rerishabh

Project: HackerRank Orchestrate September 2026: Buy or Wait


**This is the version I recommend you use now.** It documents what you actually built, your verified result, the leaderboard, and the post-hackathon feedback without claiming that the submitted code was more agentic than HackerRank's own review says it was. The internal repository links are also relative, so they work properly when the repository is browsed or cloned. 1
