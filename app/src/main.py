from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.database import init_db
from src.leads import router as leads_router
from src.market import router as market_router
from src.webhooks import router as webhook_router


@asynccontextmanager
async def lifespan(_app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Clearpath Lead Intelligence API", lifespan=lifespan)

app.include_router(webhook_router, prefix="/webhooks")
app.include_router(leads_router, prefix="/api")
app.include_router(market_router, prefix="/api")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "clearpath-api"}
