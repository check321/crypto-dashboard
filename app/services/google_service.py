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
from pathlib import Path
import aiofiles

class GoogleService:
    def __init__(self):
        self.base_url = "https://www.google.com/finance/quote"
        self.search_url = "https://www.google.com/search"
        self.headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/119.0"
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
        从Google Finance获取价格信息，支持缓存
        """
        try:
            # 格式化交易对
            formatted_symbol = self._format_symbol(symbol)
            
            # 检查缓存
            cache_data = await self._read_cache()
            if symbol in cache_data:
                cache_entry = cache_data[symbol]
                if self._is_cache_valid(cache_entry["timestamp"]):
                    logger.info(f"Cache hit for symbol: {symbol}")
                    return cache_entry
            
            # 如果缓存不存在或已过期，从Google Finance获取数据
            formatted_symbol = formatted_symbol.replace("/", "-")  # 转换为Google Finance格式
            logger.info(f"Fetching from Google Finance for: {formatted_symbol}")
            logger.info(f"Using proxy: {self.proxy}")
            
            # 使用SSL和代理配置
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            timeout = aiohttp.ClientTimeout(total=10, connect=5)
            
            async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
                async with session.get(
                    f"{self.base_url}/{formatted_symbol}",
                    proxy=self.proxy if self.proxy else None,
                    timeout=timeout
                ) as response:
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"Failed to fetch data from Google Finance: HTTP {response.status}"
                        )
                    
                    html = await response.text()
                    price_info = self._extract_price_from_finance(html, formatted_symbol)
                    
                    # 构建响应数据
                    result = {
                        "symbol": symbol,
                        "exchange": "Google Finance",
                        "bid_price": price_info["price"],
                        "ask_price": price_info["price"],
                        "last_price": price_info["price"],
                        "bid_qty": 0,
                        "ask_qty": 0,
                        "volume_24h": price_info.get("volume_24h", 0),
                        "timestamp": datetime.now().isoformat(),
                        "price_change_24h": price_info.get("price_change_24h", 0),
                        "price_change_percent": price_info.get("price_change_percent", 0)
                    }
                    
                    # 更新缓存
                    cache_data[symbol] = result
                    await self._write_cache(cache_data)
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Failed to fetch price from Google Finance: {str(e)}")
            # 尝试返回缓存数据
            cache_data = await self._read_cache()
            if symbol in cache_data:
                logger.info(f"Returning cached data for {symbol} after error")
                return cache_data[symbol]
            # 如果没有缓存数据，则抛出异常
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch price from Google Finance: {str(e)}"
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
    
    def _extract_price_from_finance(self, html: str, symbol: str) -> dict:
        """从Google Finance页面提取价格信息"""
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # 保存HTML以供调试
            debug_file = self.cache_dir / "last_google_finance_response.html"
            try:
                with open(debug_file, 'w', encoding='utf-8') as f:
                    f.write(html)
            except Exception as e:
                logger.warning(f"Failed to save debug HTML: {e}")

            # Google Finance特定的价格选择器
            price_selectors = [
                {'class': 'YMlKec fxKbKc'},  # 主价格
                {'class': 'kf1m0'},          # 备选价格类1
                {'class': 'P6K39c'},         # 备选价格类2
            ]
            
            # 尝试找到价格元素
            price_element = None
            for selector in price_selectors:
                price_element = soup.find(['div', 'span'], selector)
                if price_element:
                    break
            
            if not price_element:
                raise ValueError(f"Price element not found for {symbol}")
            
            # 提取价格文本
            price_text = price_element.text.strip()
            logger.debug(f"Found price text: {price_text}")
            
            # 移除货币符号并提取数字
            price_text = re.sub(r'[^\d,.]', '', price_text)
            
            # 处理不同的千位分隔符和小数点格式
            if ',' in price_text and '.' in price_text:
                comma_index = price_text.index(',')
                dot_index = price_text.index('.')
                if comma_index > dot_index:
                    price_text = price_text.replace('.', '').replace(',', '.')
                else:
                    price_text = price_text.replace(',', '')
            elif ',' in price_text and '.' not in price_text:
                if len(price_text.split(',')[1]) == 2:
                    price_text = price_text.replace(',', '.')
                else:
                    price_text = price_text.replace(',', '')
            
            price = Decimal(price_text)
            if price <= 0:
                raise ValueError(f"Invalid price value: {price}")
            
            # 尝试提取其他信息
            result = {"price": float(price)}
            
            # 提取24小时成交量
            volume_element = soup.find(['div', 'span'], string=re.compile(r'Volume|成交量'))
            if volume_element:
                volume_text = volume_element.find_next(['div', 'span']).text.strip()
                volume_match = re.search(r'[\d,.]+[KMB]?', volume_text)
                if volume_match:
                    volume = self._parse_volume(volume_match.group())
                    result["volume_24h"] = volume
            
            # 提取价格变化
            change_element = soup.find(['div', 'span'], {'class': 'JwB6zf'})
            if change_element:
                change_text = change_element.text.strip()
                change_match = re.search(r'([+-]?[\d,.]+)\s*\(([+-]?[\d,.]+)%\)', change_text)
                if change_match:
                    result["price_change_24h"] = float(change_match.group(1).replace(',', ''))
                    result["price_change_percent"] = float(change_match.group(2).replace(',', ''))
            
            logger.info(f"Successfully extracted price info from Google Finance for {symbol}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to extract price from Google Finance: {str(e)}")
            # 保存失败的HTML以供调试
            error_file = self.cache_dir / f"google_finance_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            try:
                with open(error_file, 'w', encoding='utf-8') as f:
                    f.write(html)
                logger.info(f"Saved error HTML to {error_file}")
            except Exception as write_err:
                logger.warning(f"Failed to save error HTML: {write_err}")
            raise ValueError(f"Could not extract price information from Google Finance for {symbol}: {str(e)}")

    def _parse_volume(self, volume_text: str) -> float:
        """解析成交量文本，处理K/M/B等单位"""
        try:
            multiplier = 1
            if volume_text.endswith('K'):
                multiplier = 1000
                volume_text = volume_text[:-1]
            elif volume_text.endswith('M'):
                multiplier = 1000000
                volume_text = volume_text[:-1]
            elif volume_text.endswith('B'):
                multiplier = 1000000000
                volume_text = volume_text[:-1]
            
            volume = float(volume_text.replace(',', ''))
            return volume * multiplier
        except Exception as e:
            logger.warning(f"Failed to parse volume: {volume_text}, error: {e}")
            return 0 