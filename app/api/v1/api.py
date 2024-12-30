from fastapi import APIRouter
from api.v1.endpoints import health, crypto, power

api_router = APIRouter()

api_router.include_router(
    health.router,
    tags=["health"]
)

api_router.include_router(
    crypto.router,
    prefix="/crypto",
    tags=["crypto"]
)

api_router.include_router(
    power.router,
    prefix="/power",
    tags=["power"]
) 