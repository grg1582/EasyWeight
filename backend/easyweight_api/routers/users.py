from fastapi import APIRouter, Depends

from ..auth import current_user
from ..demo import is_demo
from ..models import User
from ..schemas import UserOut

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    """The signed-in user"""
    return UserOut(id=user.id, email=user.email, created_at=user.created_at,
                   is_demo=is_demo(user))
