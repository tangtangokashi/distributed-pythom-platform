from contextlib import asynccontextmanager

from fastapi import FastAPI
from nicegui import ui

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

# Page registration must happen before NiceGUI is attached to FastAPI.
# Do not use ``import app.frontend`` here: that would overwrite this module's
# FastAPI ``app`` variable with the Python package object.
from app import frontend as _frontend  # noqa: E402,F401

ui.run_with(app, storage_secret="replace-this-in-production", title="分布式实时智能决策平台", favicon="◈")
