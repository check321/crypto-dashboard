import aiohttp
from fastapi import HTTPException
from datetime import datetime
from core.logging import logger
import re
from bs4 import BeautifulSoup
from decimal import Decimal
from core.config import settings
import ssl

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
    
    async def get_price(self, symbol: str) -> dict:
        """
        从Google搜索获取汇率信息
        """
        try:
            # 格式化搜索查询
            formatted_symbol = self._format_symbol(symbol)
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
                    
                    return {
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