from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..db import get_db

router = APIRouter(tags=["health"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    """Is the API up, and can it reach the database? Used by Docker and hosting"""
    db.execute(text("select 1"))
    return {"status": "ok"}
