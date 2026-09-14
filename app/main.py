from fastapi import FastAPI
from .database import *
from .routers import auth


app = FastAPI(title="PixelFit",
              description="Your Generative AI Fitness Buddy")

Base.metadata.create_all(bind=engine)

app.include_router(auth.router)