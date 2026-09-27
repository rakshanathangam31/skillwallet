from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.routes import router
from app.database import init_db

init_db()

app = FastAPI(title="FitBuddy - AI Fitness Plan Generator")

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)