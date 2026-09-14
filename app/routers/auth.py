from fastapi import APIRouter, Depends, status
from ..database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from ..models import User
from pwdlib import PasswordHash


router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


database_dependency = Annotated[Session, Depends(get_db)]

password_hash = PasswordHash.recommended()


class UserModel(BaseModel):
    email: EmailStr = Field(examples=["johndoe@email.com"])
    username: str = Field(min_length=3, max_length=30,
                          pattern=r"^[a-z0-9_-]+$",
                          description=" Lowercase Alphanumeric, underscores, and hyphens only",
                          examples=["johndoe"])
    f_name: str = Field(min_length=1, max_length=50,
                        pattern=r"^[a-zA-Z\s\-']+$",
                        description="First name, letters, spaces, hyphens, and apostrophes only",
                        examples=["John"])
    l_name: str = Field(min_length=1, max_length=50,
                        pattern=r"^[a-zA-Z\s\-']+$",
                        description="Last name, letters, spaces, hyphens, and apostrophes only",
                        examples=["Doe"])
    plain_password: str = Field(min_length=8, max_length=64,
                                description="minimum 8 characters, maximum 64 characters",
                                examples=["your_password"])


class UserResponse(BaseModel):
    username: str
    email: str
    f_name: str
    l_name: str

    class Config:
        from_attributes = True


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
def register_user(db: database_dependency, new_user: UserModel):
    user = User(
        email = new_user.email,
        username = new_user.username,
        f_name = new_user.f_name,
        l_name = new_user.l_name,
        hashed_password = password_hash.hash(new_user.plain_password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user