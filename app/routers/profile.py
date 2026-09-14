from fastapi import APIRouter, Depends, HTTPException, status
from ..database import SessionLocal
from typing import Annotated
from sqlalchemy.orm import Session
from .auth import current_user_auth
from pydantic import BaseModel, Field
from ..models import Profile, Sex, ActivityLevel, Goal


router = APIRouter(prefix = "/profile", tags = ["Profile"])



###  DEPENDENCIES
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

database_dependency = Annotated[Session, Depends(get_db)]

user_dependency = Annotated[dict, Depends(current_user_auth)]



###  PYDANTIC MODELS
class ProfileModel(BaseModel):
    age: int = Field(gt=13, lt=120,
                     description="Age in years, must be between 14 and 119",
                     examples=[22])
    sex: Sex = Field(
        description="Biological sex used for calculating BMR",
        examples=["male"]
    )
    height_cm: int = Field(gt=50, lt=250,
                           description="Height in centimeters, must be between 51 and 249 cm",
                           examples=[175])
    weight_kg: int = Field(gt=20, lt=500,
                           description="Body weight in kilograms, must be between 20 and 500 kg",
                           examples=[72.5])
    activity_level: ActivityLevel = Field(
        description="Daily physical activity level used for calculating TDEE",
        examples=["moderate"]
    )
    goal: Goal = Field(
        description="Fitness goal used to determine the user's target calorie intake",
        examples=["lose"]
    )


class ProfileResponse(BaseModel):
    id: int
    user_id: int
    age: int
    sex: Sex
    height_cm: int
    weight_kg: int
    activity_level: ActivityLevel
    goal: Goal
    bmr: int
    bmi: float
    tdee: int



###  CALCULATION FUNCTION
def calculate_bmr_bmi_tdee(age: int, sex: Sex, height_cm:int,
                      weight_kg:int, activity_level: ActivityLevel):
    if sex==Sex.MALE:
        bmr = (10*weight_kg) + (6.25*height_cm) - (5*age) + 5
    elif sex == Sex.FEMALE:
        bmr = (10*weight_kg) + (6.25*height_cm) - (5*age) - 161
    height_m: float = height_cm / 100
    bmi = weight_kg / height_m**2
    if activity_level==ActivityLevel.SEDENTARY:
        activity_factor = 1.2
    elif activity_level==ActivityLevel.LIGHT:
        activity_factor = 1.375
    elif activity_level==ActivityLevel.MODERATE:
        activity_factor = 1.55
    elif activity_level == ActivityLevel.VERY_ACTIVE:
        activity_factor = 1.725
    tdee = bmr * activity_factor
    return {
        "bmr" : round(bmr),
        "bmi" : round(bmi, 2),
        "tdee" : round(tdee)
        }


"""===========================================ENDPOINTS==========================================="""
@router.post(path="/", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
def create_profile(db: database_dependency, user: user_dependency, profile: ProfileModel):
    existing_profile = db.query(Profile).filter(Profile.user_id == user.get("id")).first()
    if existing_profile is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User already has a profile"
        )
    user_stats = calculate_bmr_bmi_tdee(profile.age, profile.sex, profile.height_cm,
                                        profile.weight_kg, profile.activity_level)
    user_profile = Profile(
        user_id = user.get("id"),
        age = profile.age,
        sex = profile.sex,
        height_cm = profile.height_cm,
        weight_kg = profile.weight_kg,
        activity_level = profile.activity_level,
        goal = profile.goal,
        bmr = user_stats["bmr"],
        bmi = user_stats["bmi"],
        tdee = user_stats["tdee"]
    )
    db.add(user_profile)
    db.commit()
    db.refresh(user_profile)
    return user_profile