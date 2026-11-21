import uuid

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..auth import current_user
from ..db import get_db
from ..demo import not_demo
from ..models import Device, User
from ..schemas import DeviceCreate, DeviceCreated, DeviceOut
from ..security import current_device, hash_token, new_token

router = APIRouter(prefix="/api/v1/devices", tags=["devices"])


@router.post("", response_model=DeviceCreated, status_code=status.HTTP_201_CREATED)
def register_device(body: DeviceCreate, user: User = Depends(not_demo),
                    db: Session = Depends(get_db)):
    """Register a mirror to the signed-in user. The token in the answer is
    shown only this once: the mirror keeps it and sends it with its events"""
    token = new_token()
    device = Device(name=body.name, token_hash=hash_token(token), owner_id=user.id)
    db.add(device)
    db.commit()
    return DeviceCreated(**DeviceOut.model_validate(device).model_dump(), token=token)


@router.get("", response_model=list[DeviceOut])
def my_devices(user: User = Depends(current_user), db: Session = Depends(get_db)):
    """The signed-in user's mirrors, oldest first"""
    return db.scalars(
        select(Device).where(Device.owner_id == user.id).order_by(Device.created_at)
    ).all()


@router.get("/me", response_model=DeviceOut)
def this_device(device: Device = Depends(current_device)):
    """The device the token belongs to. A mirror calls it to check its token works"""
    return device


@router.delete("/{device_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_device(device_id: uuid.UUID, user: User = Depends(not_demo),
                  db: Session = Depends(get_db)):
    """Remove a mirror and everything it recorded. Its token stops working"""
    device = db.get(Device, device_id)
    if device is None or device.owner_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Device not found")
    # The database deletes its workouts and events too (ON DELETE CASCADE)
    db.execute(delete(Device).where(Device.id == device.id))
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
