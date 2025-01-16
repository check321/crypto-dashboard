import aiohttp
from fastapi import HTTPException
from datetime import datetime, timedelta
from core.logging import logger
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from core.config import settings
import ssl
import json
import os
from pathlib import Path
import aiofiles

class GoogleService:
    def __init__(self):
        self.base_url = "https://www.google.com/search"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        # 配置SSL
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        # 使用配置的代理
        self.proxy = settings.HTTPS_PROXY if settings.HTTPS_PROXY != "" else None
        
        # 缓存配置
        self.cache_dir = Path("cache")
        self.cache_file = self.cache_dir / "google_price_cache.json"
        self.cache_expire_minutes = settings.GOOGLE_CACHE_EXPIRE_MINUTES
        self._ensure_cache_dir()
    
    def _ensure_cache_dir(self):
        """确保缓存目录存在"""
        self.cache_dir.mkdir(exist_ok=True)
        if not self.cache_file.exists():
            self.cache_file.write_text("{}")
    
    async def _read_cache(self) -> dict:
        """读取缓存数据"""
        try:
            async with aiofiles.open(self.cache_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to read cache: {str(e)}")
            return {}
    
    async def _write_cache(self, cache_data: dict):
        """写入缓存数据"""
        try:
            async with aiofiles.open(self.cache_file, 'w') as f:
                await f.write(json.dumps(cache_data, indent=2))
        except Exception as e:
            logger.error(f"Failed to write cache: {str(e)}")
    
    def _is_cache_valid(self, cache_time: str) -> bool:
        """检查缓存是否有效"""
        try:
            cache_datetime = datetime.fromisoformat(cache_time)
            expire_time = cache_datetime + timedelta(minutes=self.cache_expire_minutes)
            return datetime.now() < expire_time
        except Exception:
            return False
    
    async def get_price(self, symbol: str) -> dict:
        """
        从Google搜索获取汇率信息，支持缓存
        """
        try:
            # 格式化搜索查询
            formatted_symbol = self._format_symbol(symbol)
            
            # 检查缓存
            cache_data = await self._read_cache()
            if symbol in cache_data:
                cache_entry = cache_data[symbol]
                return cache_entry
                # TODO: cache policy.
                # if self._is_cache_valid(cache_entry["timestamp"]):
                #     logger.info(f"Cache hit for symbol: {symbol}")
                #     return cache_entry
            
            # 如果缓存不存在或已过期，从Google获取数据
            query = f"{formatted_symbol} price"
            logger.info(f"Searching Google for: {query}")
            logger.info(f"Using proxy: {self.proxy}")
            
            # 使用SSL和代理配置
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
                async with session.get(
                    self.base_url,
                    params={"q": query},
                    proxy=self.proxy if self.proxy else None,
                    timeout=aiohttp.ClientTimeout(total=10)  # 设置超时时间
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail="Failed to fetch data from Google"
                        )
                    
                    html = await response.text()
                    price_info = self._extract_price(html, formatted_symbol)
                    
                    # 构建响应数据
                    result = {
                        "symbol": symbol,
                        "exchange": "Google",
                        "bid_price": price_info["price"],
                        "ask_price": price_info["price"],
                        "last_price": price_info["price"],
                        "bid_qty": 0,
                        "ask_qty": 0,
                        "volume_24h": 0,
                        "timestamp": datetime.now().isoformat(),
                        "price_change_24h": 0,
                        "price_change_percent": 0
                    }
                    
                    # 更新缓存
                    cache_data[symbol] = result
                    await self._write_cache(cache_data)
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Failed to fetch price from Google: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch price from Google: {str(e)}"
            )
    
    def _format_symbol(self, symbol: str) -> str:
        """格式化交易对为Google搜索格式"""
        symbol = symbol.upper()
        # 处理不同的分隔符
        symbol = symbol.replace("-", "/").replace("_", "/")
        if "/" not in symbol:
            if "JPY" in symbol:
                base = symbol.replace("JPY", "")
                return f"{base}/JPY"
            elif "USDT" in symbol:
                base = symbol.replace("USDT", "")
                return f"{base}/USDT"
        return symbol
    
    def _extract_price(self, html: str, symbol: str) -> dict:
        """从Google搜索结果中提取价格信息"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            # log html
            logger.info(f"HTML: {html}")
            # 尝试查找价格元素
            price_element = soup.find('div', {'class': 'BNeawe iBp4i AP7Wnd'})
            if not price_element:
                price_element = soup.find('div', {'class': 'BNeawe s3v9rd AP7Wnd'})
            
            if not price_element:
                raise ValueError("Price information not found")
            
            # 提取数字
            price_text = price_element.text.strip()
            price_match = re.search(r'[\d,.]+', price_text)
            if not price_match:
                raise ValueError("Could not extract price value")
            
            price = Decimal(price_match.group().replace(',', ''))
            
            return {
                "price": float(price)
            }
            
        except Exception as e:
            logger.error(f"Failed to extract price: {str(e)}")
            raise ValueError(f"Could not extract price information: {str(e)}") 