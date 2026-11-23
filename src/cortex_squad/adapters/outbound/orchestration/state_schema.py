"""LangGraph state schema and bridge models."""

import operator
from typing import Annotated, Any, TypedDict


class SquadGraphState(TypedDict):
    """LangGraph shared state carrying CoALA working memory and quorum tracking."""

    mission_id: str
    goal: str
    current_adr: str
    code_diffs: Annotated[dict[str, str], operator.or_]
    assumptions_to_attack: Annotated[list[str], operator.add]
    harness_logs: Annotated[list[str], operator.add]
    iteration_count: int
    votes: Annotated[list[dict[str, Any]], operator.add]
    approved: bool
    status_message: str
