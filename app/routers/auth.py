from fastapi import APIRouter, Depends, status, HTTPException
from ..database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, EmailStr
from ..models import User
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordRequestForm
from datetime import datetime, timezone , timedelta
from ..config import settings
from jose import jwt


router = APIRouter(prefix="/auth", tags=["Authentication"])



###  DEPENDENCIES
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

database_dependency = Annotated[Session, Depends(get_db)]

password_hash = PasswordHash.recommended()

form_dependency = Annotated[OAuth2PasswordRequestForm, Depends()]



###  PYDANTIC MODELS
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


class TokenResponse(BaseModel):
    access_token: str
    token_type: str



###  ASSIGN TOKEN FUNCTIONS
def confirm_and_get_user(username: str, plain_password: str, db: Session):
    user = db.query(User).filter(User.username==username).first()
    if user is None:
        return False
    if not password_hash.verify(plain_password, user.hashed_password):
        return False
    return user


def assign_token(id: int, username: str, role: str, time_delta):
    encode = {
        "sub" : username,
        "id" : id,
        "role" : role
    }
    exp = datetime.now(timezone.utc) + time_delta
    encode.update({"exp" : exp})
    token = jwt.encode(encode, settings.SECRET_KEY, settings.ALGORITHM)
    return token



"""===========================================ENDPOINTS==========================================="""
@router.post(path="/login""/register", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
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


@router.post(path="/login", status_code=status.HTTP_200_OK, response_model=TokenResponse)
def login_for_access_token(db: database_dependency, form_data: form_dependency):
    user = confirm_and_get_user(username = form_data.username,
                                plain_password = form_data.password,
                                db = db)
    if not user:
        raise HTTPException(
            status_code = status.HTTP_401_UNAUTHORIZED,
            detail = "Invalid Credentials."
        )
    token = assign_token(id = user.id,
                         username = user.username,
                         role = user.role,
                         time_delta = timedelta(minutes=30))
    return {
        "access_token" : token,
        "token_type" : "bearer"
        }