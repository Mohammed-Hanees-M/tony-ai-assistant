from fastapi import FastAPI

from apps.backend.api.chat import router as chat_router
from apps.backend.database.base import Base
from apps.backend.database.session import engine
from apps.backend.database.models import *

app = FastAPI(
    title="Tony",
    version="1.0.0",
    debug=True
)

Base.metadata.create_all(bind=engine)

app.include_router(
    chat_router,
    prefix="/api/chat",
    tags=["Chat"]
)


@app.get("/")
async def root():
    return {
        "message": "Tony Backend Running",
        "version": "1.0.0",
        "status": "healthy"
    }