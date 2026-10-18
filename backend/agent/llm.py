"""LLM model chain construction with provider fallback."""

from __future__ import annotations

import logging

from pydantic_ai.models import Model, infer_model
from pydantic_ai.models.fallback import FallbackModel

logger = logging.getLogger("agent.llm")


def build_model(chain: list[str]) -> Model:
    """Build a (possibly fallback-chained) model from `provider:model` specs.

    The first model in `chain` is the primary; the rest are used automatically
    when an API error / rate limit occurs (pydantic-ai's FallbackModel).
    """
    models: list[Model] = []
    used_specs: list[str] = []
    for spec in chain:
        try:
            models.append(infer_model(spec))
            used_specs.append(spec)
        except Exception as exc:  # noqa: BLE001 - a bad spec should not kill the app
            logger.warning("Skipping unusable model spec %r: %s", spec, exc)

    if not models:
        raise RuntimeError("No usable models configured. Check LLM_CHAIN in .env.")

    logger.info("LLM chain: %s", " -> ".join(used_specs))
    if len(models) == 1:
        return models[0]
    return FallbackModel(*models)
