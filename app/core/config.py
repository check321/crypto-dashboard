from pydantic_settings import BaseSettings
from typing import List
import secrets
import json
import os
from pathlib import Path

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
    
    # Telegram配置
    TG_BOT_TOKEN: str
    TG_GID: str
    
    # 定时任务配置
    @property
    def PRICE_BROADCAST_INTERVAL(self) -> int:
        config_file = Path(__file__).parent / "scheduler_config.json"
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
                return config.get("price_broadcast_interval", 5)
        except Exception:
            return 5  # 默认值
    
    @PRICE_BROADCAST_INTERVAL.setter
    def PRICE_BROADCAST_INTERVAL(self, minutes: int) -> None:
        config_file = Path(__file__).parent / "scheduler_config.json"
        try:
            config = {}
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = json.load(f)
            config["price_broadcast_interval"] = minutes
            with open(config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to update broadcast interval: {str(e)}")

    class Config:
        env_file = ".env"

settings = Settings()