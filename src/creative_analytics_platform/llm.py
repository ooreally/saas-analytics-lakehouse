from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Any, Protocol
from urllib import request

from .transforms import normalize_text


@dataclass(frozen=True)
class LLMResult:
    topic: str
    summary: str
    sentiment: str
    confidence: float
    severity_hint: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "summary": self.summary,
            "sentiment": self.sentiment,
            "confidence": self.confidence,
            "severity_hint": self.severity_hint,
        }


class LLMProvider(Protocol):
    def classify_and_summarize(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ...


class MockLLMProvider:
    """Deterministic keyword-based fallback for free and reproducible runs."""

    def classify_and_summarize(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = normalize_text(text).lower()
        context = context or {}
        priority = str(context.get("priority", "medium")).lower()

        topic = "general_product_feedback"
        sentiment = "neutral"
        severity_hint = "medium"
        confidence = 0.73

        if any(keyword in normalized for keyword in ("slow", "latency", "lag")):
            topic = "performance"
            sentiment = "negative"
            severity_hint = "high"
            confidence = 0.92
        elif any(keyword in normalized for keyword in ("fail", "error", "blank", "disappear", "bug")):
            topic = "reliability"
            sentiment = "negative"
            severity_hint = "high"
            confidence = 0.94
        elif any(keyword in normalized for keyword in ("billing", "card", "upgrade", "invoice", "plan")):
            topic = "billing"
            sentiment = "negative"
            severity_hint = "high"
            confidence = 0.9
        elif any(keyword in normalized for keyword in ("invite", "collaborator", "comment")):
            topic = "collaboration"
            sentiment = "positive" if "fast" in normalized or "intuitive" in normalized else "negative"
            severity_hint = "medium"
            confidence = 0.84
        elif any(keyword in normalized for keyword in ("checklist", "onboard", "first-run")):
            topic = "onboarding"
            sentiment = "positive"
            severity_hint = "low"
            confidence = 0.88
        elif any(keyword in normalized for keyword in ("publish", "confirmation", "success state")):
            topic = "ux_clarity"
            sentiment = "negative"
            severity_hint = "medium"
            confidence = 0.82

        if priority == "low" and severity_hint == "high":
            severity_hint = "medium"

        summary = normalize_text(text)
        if len(summary) > 96:
            summary = f"{summary[:93]}..."

        return LLMResult(
            topic=topic,
            summary=summary,
            sentiment=sentiment,
            confidence=confidence,
            severity_hint=severity_hint,
        ).as_dict()


class ExternalLLMProvider:
    def __init__(self, api_base: str, api_key: str | None = None) -> None:
        if not api_base:
            raise ValueError("api_base is required for the external LLM provider")
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key or ""

    def classify_and_summarize(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = json.dumps({"text": text, "context": context or {}}).encode("utf-8")
        request_obj = request.Request(
            url=f"{self.api_base}/classify",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )
        with request.urlopen(request_obj, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))


def build_provider(
    provider_name: str,
    api_base: str = "",
    api_key_env: str = "EXTERNAL_LLM_API_KEY",
) -> LLMProvider:
    if provider_name == "mock":
        return MockLLMProvider()
    if provider_name == "external":
        return ExternalLLMProvider(api_base=api_base, api_key=os.environ.get(api_key_env))
    raise ValueError(f"Unsupported provider: {provider_name}")

