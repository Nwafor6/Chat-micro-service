from typing import Any, Dict, Generic, List, Optional, TypeVar, Union
from urllib.parse import urlencode

from fastapi import Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.sql import Select

from app.core.database import db_context

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Generic paginated response model.
    """

    items: List[T]
    total: int
    page: int
    page_size: int
    next_page: Optional[str] = None
    previous_page: Optional[str] = None


def build_url(base_url: str, page: int, page_size: int, params: Dict[str, Any]) -> str:
    """Build URL with query parameters"""
    query_params = {k: v for k, v in params.items() if v is not None}
    query_params.update({"page": page, "page_size": page_size})
    return f"{base_url}?{urlencode(query_params)}"


async def paginate(
    request: Request,
    query_or_items: Union[Select, List],
    page: int,
    page_size: int = Query(10, description="Page size"),
) -> PaginatedResponse:
    """
    Generic pagination function that handles both SQLAlchemy queries and lists.
    """
    # Get existing query parameters
    query_params = dict(request.query_params)
    base_url = str(request.url).split("?", maxsplit=1)[0]

    # Handle SQLAlchemy query
    if isinstance(query_or_items, Select):
        db = db_context.get()
        total = await db.scalar(
            select(func.count()).select_from(query_or_items.selectable)
        )
        items = await db.scalars(
            query_or_items.offset((page - 1) * page_size).limit(page_size)
        )
        items = list(items)
    # Handle list of items
    else:
        total = len(query_or_items)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        items = query_or_items[start_idx:end_idx]

    # Calculate next and previous pages
    has_next = (page * page_size) < total
    has_previous = page > 1

    # Build URLs with all query parameters
    next_page_url = (
        build_url(base_url, page + 1, page_size, query_params) if has_next else None
    )
    previous_page_url = (
        build_url(base_url, page - 1, page_size, query_params) if has_previous else None
    )

    return PaginatedResponse[T](
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        next_page=next_page_url,
        previous_page=previous_page_url,
    )
