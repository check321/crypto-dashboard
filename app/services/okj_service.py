from fastapi import HTTPException
from datetime import datetime
import aiohttp
from core.logging import logger
from core.config import settings
import ssl

class OKJService:
    def __init__(self):
        # OKJ的API域名
        self.base_url = "https://www.okcoin.jp"
        self.ticker_endpoint = "/api/spot/v3/instruments"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
    async def get_price(self, symbol: str) -> dict:
        """
        获取OKJ指定交易对的实时买卖价格
        API文档: https://dev.okcoin.jp/zh/#spot-some
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            url = f"{self.base_url}{self.ticker_endpoint}/{formatted_symbol}/ticker"
            
            logger.debug(f"Requesting OKJ API - URL: {url}")
            
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
                async with session.get(url) as response:
                    logger.debug(f"Response status: {response.status}")
                    response_text = await response.text()
                    logger.debug(f"Response body: {response_text}")
                    
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"OKJ API request failed: {response_text}"
                        )
                        
                    ticker = await response.json()
                    
                    return {
                        "symbol": symbol,
                        "exchange": "OKJ",
                        "bid_price": float(ticker['best_bid']),
                        "bid_qty": float(ticker['best_bid_size']),
                        "ask_price": float(ticker['best_ask']),
                        "ask_qty": float(ticker['best_ask_size']),
                        "last_price": float(ticker['last']),
                        "volume_24h": float(ticker['base_volume_24h']),
                        "timestamp": ticker['timestamp'],
                        "price_change_24h": float(ticker['last']) - float(ticker['open_24h']),
                        "price_change_percent": ((float(ticker['last']) - float(ticker['open_24h'])) / float(ticker['open_24h'])) * 100
                    }
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to fetch OKJ price: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch OKJ price: {str(e)}"
            )
            
    def _format_symbol(self, symbol: str) -> str:
        """
        将统一格式的交易对转换为OKJ格式
        BTCJPY -> BTC_JPY
        """
        symbol = symbol.upper()
        if '_' not in symbol:
            if 'JPY' in symbol:
                base = symbol.replace('JPY', '')
                return f"{base}_JPY"
        return symbol 