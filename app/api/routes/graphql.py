from fastapi import APIRouter

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/")
def read_root() -> dict[str, str]:
    """Return a demo greeting at the API root."""
    return {"Hello": "World"}


@router.get("/items/{item_id}")
def read_item(item_id: int, q: str | None = None) -> dict[str, object]:
    """Echo the requested ``item_id`` and an optional URL query ``q``."""
    return {"item_id": item_id, "q": q}
