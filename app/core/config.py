from pydantic_settings import BaseSettings
from typing import List
import secrets

class Settings(BaseSettings):
    PROJECT_NAME: str = "FastAPI Project"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "FastAPI项目模板"
    API_V1_STR: str = "/api/v1"
    
    # 安全配置
    SECRET_KEY: str = secrets.token_urlsafe(32)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # 数据库配置
    DATABASE_URL: str
    
    # CORS配置
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # 代理设置
    HTTP_PROXY: str = "http://127.0.0.1:7890"  # 根据你的代理设置调整
    HTTPS_PROXY: str = "http://127.0.0.1:7890"  # 根据你的代理设置调整
    
    # Google服务配置
    GOOGLE_CACHE_EXPIRE_MINUTES: int = 30  # Google价格缓存过期时间（分钟）
    
    # 配置文件路径
    DATA_DIR: str = "data"
    POWER_CONFIG_FILE: str = "g-power.json"
    
    class Config:
        env_file = ".env"

settings = Settings() 