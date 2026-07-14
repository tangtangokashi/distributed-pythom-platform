from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import router
from app.config import get_settings
from app.database import Base, engine
from app.services.realtime import realtime


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    realtime.seed()
    settings = get_settings()
    if settings.simulation_autostart:
        await realtime.start(settings.simulation_interval_seconds)
    yield
    await realtime.stop()


app = FastAPI(title="Distributed Intelligent Decision Platform", version="1.0.0", lifespan=lifespan)
app.include_router(router)
