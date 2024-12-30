from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.v1.api import api_router
import uvicorn
from core.logging import logger

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