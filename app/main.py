from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.v1.api import api_router
import uvicorn
from core.logging import logger
import asyncio
from api.v1.endpoints.crypto import get_compose_price_by_period
from apscheduler.schedulers.asyncio import AsyncIOScheduler

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

logger.info("Starting application...")

# CORS设置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)

# 初始化定时任务调度器
scheduler = AsyncIOScheduler()

@app.on_event("startup")
async def startup_event():
    # 添加定时任务
    scheduler.add_job(
        get_compose_price_by_period,
        'interval',
        minutes=settings.PRICE_BROADCAST_INTERVAL,
        id='price_broadcast'
    )
    # 启动调度器
    scheduler.start()
    logger.info(f"Started price broadcast scheduler with interval {settings.PRICE_BROADCAST_INTERVAL} seconds")

@app.on_event("shutdown")
async def shutdown_event():
    # 关闭调度器
    scheduler.shutdown()
    logger.info("Stopped price broadcast scheduler")

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# 添加这段代码用于直接运行
if __name__ == "__main__":
    # 设置uvicorn的日志配置
    uvicorn.run(
        "main:app",  
        host="0.0.0.0",
        port=7700,
        reload=True,
        workers=1,
    )