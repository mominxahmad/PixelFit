from .database import Base
from sqlalchemy import (Column, Integer, Float, String, ForeignKey,
                        Enum as SQLEnum)
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
    role = Column(SQLEnum(Role), default=Role.USER, nullable=False)


class Sex(Enum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(Enum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    VERY_ACTIVE = "very_active"


class Goal(Enum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    age = Column(Integer, nullable=False)
    sex = Column(SQLEnum(Sex), nullable=False)
    height_cm = Column(Integer, nullable=False)
    weight_kg = Column(Integer, nullable=False)
    activity_level = Column(SQLEnum(ActivityLevel), nullable=False)
    goal = Column(SQLEnum(Goal), nullable=False)
    bmr = Column(Integer, nullable=False)
    bmi = Column(Float, nullable=False)
    tdee = Column(Integer, nullable=False)