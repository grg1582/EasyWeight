from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Device
from ..schemas import DeviceCreate, DeviceCreated, DeviceOut
from ..security import current_device, hash_token, new_token

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("", response_model=DeviceCreated, status_code=status.HTTP_201_CREATED)
def register_device(body: DeviceCreate, db: Session = Depends(get_db)):
    """Register a mirror. The token in the answer is shown only this once.

    Open to anyone for now. Phase 4 (user accounts) limits it to signed-in users"""
    token = new_token()
    device = Device(name=body.name, token_hash=hash_token(token))
    db.add(device)
    db.commit()
    return DeviceCreated(**DeviceOut.model_validate(device).model_dump(), token=token)


@router.get("/me", response_model=DeviceOut)
def this_device(device: Device = Depends(current_device)):
    """The device the token belongs to. A mirror calls it to check its token works"""
    return device
