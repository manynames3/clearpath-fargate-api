from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, status

from src.analytics import router as analytics_router
from src.database import check_database_ready, init_db
from src.dashboard import router as dashboard_router
from src.intelligence import router as intelligence_router
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
app.include_router(intelligence_router, prefix="/api")
app.include_router(analytics_router, prefix="/api")
app.include_router(dashboard_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "clearpath-api"}


@app.get("/ready")
async def ready():
    try:
        await check_database_ready()
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    return {"status": "ready", "service": "clearpath-api"}
