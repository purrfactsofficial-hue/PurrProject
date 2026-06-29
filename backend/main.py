from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import create_tables
from routes import analytics, captions, schedule, videos
from routes.media import router as media_router
from routes.schedule_publish import router as schedule_publish_router
from scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    settings.thumbs_dir.mkdir(parents=True, exist_ok=True)
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="PurrFacts API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(videos.router)
app.include_router(captions.router)
app.include_router(schedule_publish_router)
app.include_router(schedule.router)
app.include_router(analytics.router)
app.include_router(media_router)

app.mount("/thumbs", StaticFiles(directory=str(settings.thumbs_dir)), name="thumbs")


@app.get("/health")
def health():
    return {"status": "ok"}
