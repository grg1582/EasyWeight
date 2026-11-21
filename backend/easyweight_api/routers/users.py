from fastapi import APIRouter, Depends

from ..auth import current_user
from ..models import User
from ..schemas import UserOut

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    """The signed-in user"""
    return user
