"""One explicit OpenAI reasoning profile; no credentials or live discovery here."""
import copy
import getpass
import sys
import warnings

NAME = "openai-reasoning"
TARGET = {"provider": "openai", "model": "gpt-5.6-sol", "endpoint": "https://api.openai.com/v1"}
GENERATOR = "openai.OpenAIReasoningGenerator"
COMPLETION_LIMIT = 1500
SUPPRESSED = ["n", "temperature", "max_tokens", "stop", "top_p", "frequency_penalty", "presence_penalty", "seed"]


def targets(cfg):
    result = copy.deepcopy(cfg["targets"])
    result.setdefault(NAME, dict(TARGET))
    return result


def campaign_settings(campaign):
    result = copy.deepcopy(campaign)
    limit = result.get("max_completion_tokens", COMPLETION_LIMIT)
    result.pop("max_tokens", None)
    result.pop("temperature", None)
    result.update({"max_completion_tokens": limit, "generator_seed": None,
                   "reasoning_effort": "API default; not specified", "temperature_policy": "not sent",
                   "experimental_effect": f"New OpenAI experiment: probe sampling seed 42; no generation seed or temperature sent; {limit} total completion tokens including reasoning; sequential requests. Not comparable to Ollama's 256-token setting.",
                   "api_use": "Paid OpenAI target: one compatibility generation, then the selected probe. No auxiliary model/API."})
    result["workload"].setdefault("http_request_limit", None)
    result["workload"]["planned_http_requests"] = (result["workload"].get("expected_attempts") or result["workload"]["attempt_cap"]) + 1
    return result


def read_session_key():
    """Refuse getpass's echoing fallback. Never write to profiles or os.environ."""
    if not sys.stdin.isatty():
        raise ValueError("OpenAI requires an interactive terminal for hidden API-key entry.")
    with warnings.catch_warnings():
        warnings.simplefilter("error", getpass.GetPassWarning)
        try:
            key = getpass.getpass("OpenAI API key (hidden; this runner session only; Enter cancels): ")
        except (getpass.GetPassWarning, EOFError, KeyboardInterrupt):
            return None
    if not key:
        return None
    if any(ord(ch) < 33 or ord(ch) > 126 for ch in key):
        raise ValueError("API key must contain printable ASCII without whitespace; value was not recorded.")
    return key
