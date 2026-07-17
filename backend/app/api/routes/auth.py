import logging
import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from motor.motor_asyncio import AsyncIOMotorDatabase

from app.db.database import get_db
from app.core.security import (
    hash_password, verify_password, create_access_token, get_current_user
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    full_name: str
    role: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    try:
        existing = await db.users.find_one({"email": req.email})
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered")

        user_count = await db.users.count_documents({})
        user_id = str(uuid.uuid4())
        role = "admin" if user_count == 0 else "user"

        user_doc = {
            "_id": user_id,
            "email": req.email,
            "hashed_password": hash_password(req.password),
            "full_name": req.full_name,
            "role": role,
            "is_active": True,
            "created_at": datetime.utcnow(),
        }

        await db.users.insert_one(user_doc)

        token = create_access_token({"sub": user_id})
        
        return TokenOut(
            access_token=token,
            user=UserOut(
                id=user_id,
                email=req.email,
                full_name=req.full_name,
                role=role
            )
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Register failed")
        raise


@router.post("/login", response_model=TokenOut)
async def login(req: LoginRequest, db: AsyncIOMotorDatabase = Depends(get_db)):
    user = await db.users.find_one({"email": req.email})
    if not user or not verify_password(req.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")

    token = create_access_token({"sub": user["_id"]})
    
    return TokenOut(
        access_token=token,
        user=UserOut(
            id=user["_id"],
            email=user["email"],
            full_name=user["full_name"],
            role=user["role"]
        )
    )


@router.get("/me", response_model=UserOut)
async def me(current_user: dict = Depends(get_current_user)):
    return UserOut(
        id=current_user["id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        role=current_user["role"]
    )
