from config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.declarative import declarative_base


engine = create_engine(settings.DATABASE_URL)

SessionLocal = Session(bind=engine, autocommit=False, autoflush=False)

Base = declarative_base()
