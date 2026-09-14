from .database import Base
from sqlalchemy import (Column, Integer, String, ForeignKey, DateTime,
                        Enum as SQLEnum)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from enum import Enum


class Role(Enum):
    ADMIN = "admin"
    USER = "user"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    f_name = Column(String, nullable=False)
    l_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String,SQLEnum(Role), default="user", nullable=False)