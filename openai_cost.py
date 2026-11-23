"""Transparent estimates and optional alerts; never an account-credit control."""
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path


def money(value, *, positive=False):
    try:
        result = Decimal(str(value))
    except InvalidOperation:
        raise ValueError("Enter a decimal USD amount.") from None
    if not result.is_finite() or result < 0 or (positive and result <= 0):
        raise ValueError("Amount must be finite and " + ("positive." if positive else "nonnegative."))
    return result


def published_rates(model, today=None):
    try:
        rates = json.loads((Path(__file__).parent / "openai-pricing.json").read_text(encoding="utf-8"))
        current = today or date.today()
        if rates["model"] != model or not date.fromisoformat(rates["verified_on"]) <= current <= date.fromisoformat(rates["valid_through"]):
            return None
        for field in ("input_usd_per_million", "output_usd_per_million", "cached_input_usd_per_million"):
            money(rates[field])
        return rates
    except (OSError, ValueError, KeyError, TypeError):
        return None


def input_units(messages):
    return len(json.dumps(messages, ensure_ascii=False).encode("utf-8")) + 64


def estimate(campaign):
    rates, inputs = campaign.get("pricing"), campaign.get("input_estimate")
    if not rates or not inputs:
        return None
    calls = campaign["workload"].get("http_request_limit") or campaign["workload"]["planned_http_requests"]
    input_budget = inputs["max_input_units_per_request"] * calls
    output_budget = campaign["max_completion_tokens"] * calls
    total = (Decimal(input_budget) * money(rates["input_usd_per_million"]) +
             Decimal(output_budget) * money(rates["output_usd_per_million"])) / 1000000
    return {"estimated_usd": str(total.quantize(Decimal("0.000001"))),
            "requests": calls, "input_planning_units": input_budget, "completion_token_ceiling": output_budget,
            "method": "Configured request cap when set, otherwise planned workload plus one compatibility call; longest sampled input's UTF-8 JSON byte length plus 64 units, and full completion limit. Retries consume the same counter if any occur. Conservative planning estimate, not measured input tokens, a dollar cap or a billing guarantee."}


class StopRequested(RuntimeError):
    pass


class Tracker:
    def __init__(self, folder, campaign):
        self.path = Path(folder) / "openai-cost.json"
        self.rates = campaign.get("pricing")
        self.alert = money(campaign["spending_alert_usd"], positive=True) if campaign.get("spending_alert_usd") else None
        self.total = Decimal(0)
        self.missing = 0
        self.events = []

    def save(self):
        self.path.write_text(json.dumps({"estimated_reported_usage_usd": str(self.total) if self.rates else None,
            "missing_usage_responses": self.missing, "rates": self.rates,
            "spending_alert_usd": str(self.alert) if self.alert is not None else None,
            "events": self.events, "note": "Usage-based estimate, not an invoice or credit balance. Alerts never override the request cap."}, indent=2) + "\n", encoding="utf-8")

    def after_response(self, body, sequence, stage):
        usage = body.get("usage") if isinstance(body, dict) else None
        cost = None
        if isinstance(usage, dict) and all(type(usage.get(k)) is int and usage[k] >= 0 for k in ("prompt_tokens", "completion_tokens")):
            if self.rates:
                details = usage.get("prompt_tokens_details") or {}
                cached = details.get("cached_tokens", 0)
                cached = cached if type(cached) is int and 0 <= cached <= usage["prompt_tokens"] else 0
                cost = ((usage["prompt_tokens"] - cached) * money(self.rates["input_usd_per_million"]) +
                        cached * money(self.rates.get("cached_input_usd_per_million", self.rates["input_usd_per_million"])) +
                        usage["completion_tokens"] * money(self.rates["output_usd_per_million"])) / 1000000
                self.total += cost
        else:
            self.missing += 1
        self.events.append({"sequence": sequence, "stage": stage, "usage": usage,
                            "estimated_usd": str(cost) if cost is not None else None})
        self.save()
        if self.rates:
            print(f"Running estimated API total: ${self.total:.6f} from reported usage; {self.missing} response(s) missing usage.", flush=True)
        else:
            print("Running cost: Estimate unavailable (no verified or supplied rate); reported usage is retained.", flush=True)

    def before_request(self):
        if self.alert is None or self.rates is None or self.total < self.alert:
            return
        while True:
            print(f"\nOptional spending alert reached: estimated ${self.total:.6f}; alert ${self.alert}. No next request sent.")
            print("[1] Continue (one more request)\n[2] Raise alert\n[3] Stop")
            try:
                choice = input("Selection (Enter stops): ").strip().lower()
                if choice in ("1", "continue"):
                    self.events.append({"action": "continue_one_request", "estimated_total_usd": str(self.total)})
                    self.save()
                    return
                if choice in ("2", "raise alert"):
                    amount = money(input("New alert in USD: ").strip(), positive=True)
                    if amount <= self.total:
                        print("New alert must exceed the current estimated total.")
                        continue
                    self.alert = amount
                    self.events.append({"action": "raise_alert", "new_alert_usd": str(amount)})
                    self.save()
                    return
                if choice in ("", "3", "stop"):
                    break
                print("Choose Continue, Raise alert, or Stop.")
            except ValueError as exc:
                print(str(exc))
            except (EOFError, KeyboardInterrupt):
                break
        self.events.append({"action": "stop_before_next_request", "estimated_total_usd": str(self.total)})
        self.save()
        raise StopRequested("Operator stopped at the optional spending alert; no next paid request sent.")
