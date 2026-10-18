"""Structured output schema for the Deal Finder agent."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GroupChoice(BaseModel):
    """One product the agent believes is the same item across marketplaces."""

    canonical_name: str = Field(
        description="Short, specific product name, e.g. 'Sony WH-1000XM5'. Include the model/variant when known."
    )
    offer_ids: list[int] = Field(
        description="IDs (from the search results) of listings that refer to this same product."
    )
    note: str = Field(
        default="",
        description="One line explaining why these listings were grouped together.",
    )


class BestDeal(BaseModel):
    """The single best deal the agent recommends."""

    offer_id: int = Field(description="ID of the recommended listing from the search results.")
    group_index: int = Field(description="Index of the group (in `groups`) that contains this listing.")
    reason: str = Field(
        description="One or two sentences explaining why this listing is the best deal (price, delivery, rating, seller trustworthiness)."
    )


class DealReport(BaseModel):
    """Final structured answer produced by the agent."""

    query_understood: str = Field(
        description="What the user is looking for, restated as clean product search terms."
    )
    groups: list[GroupChoice] = Field(
        default_factory=list,
        description="Distinct products found, each with the listings that belong to it.",
    )
    best_deal: BestDeal | None = Field(
        default=None,
        description="The recommended deal, or null when a sensible recommendation is impossible.",
    )
    summary: str = Field(
        description="A 2-4 sentence summary for the shopper: what was found, the price range, and the headline recommendation."
    )
    caveats: list[str] = Field(
        default_factory=list,
        description="Short caveats such as missing marketplaces, demo data, or low-confidence matches.",
    )
