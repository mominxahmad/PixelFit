from fastapi import FastAPI
from .database import *
from .routers import auth, profile, meal_plan, report

app = FastAPI(title="PixelFit",
              description="Your Generative AI Fitness Buddy")

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(meal_plan.router)