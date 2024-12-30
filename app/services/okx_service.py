from fastapi import HTTPException
from datetime import datetime
import aiohttp
from core.logging import logger
from core.config import settings
import ssl

class OKXService:
    def __init__(self):
        self.base_url = "https://www.okx.com"
        self.ticker_endpoint = "/api/v5/market/ticker"
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE
        
        # 配置代理
        self.proxy = settings.HTTPS_PROXY
        
    async def get_price(self, symbol: str) -> dict:
        """
        获取OKX指定交易对的实时买卖价格
        API文档: https://www.okx.com/docs-v5/en/#order-book-trading-market-data-get-ticker
        """
        try:
            formatted_symbol = self._format_symbol(symbol)
            url = f"{self.base_url}{self.ticker_endpoint}"
            params = {
                "instId": formatted_symbol,
            }
            
            logger.debug(f"Requesting OKX API - URL: {url}")
            logger.debug(f"Using proxy: {self.proxy}")
            
            # 使用代理配置创建连接器
            connector = aiohttp.TCPConnector(ssl=self.ssl_context)
            async with aiohttp.ClientSession(headers=self.headers, connector=connector) as session:
                async with session.get(
                    url, 
                    params=params,
                    # proxy=self.proxy
                ) as response:
                    logger.debug(f"Response status: {response.status}")
                    response_text = await response.text()
                    logger.debug(f"Response body: {response_text}")
                    
                    if response.status != 200:
                        raise HTTPException(
                            status_code=response.status,
                            detail=f"OKX API request failed: {response_text}"
                        )
                        
                    data = await response.json()
                    
                    if data['code'] != '0':
                        raise HTTPException(
                            status_code=400,
                            detail=f"OKX API error: {data['msg']}"
                        )
                    
                    ticker = data['data'][0]
                    result = {
                        "symbol": symbol,
                        "exchange": "OKX",
                        "bid_price": float(ticker['bidPx']),
                        "bid_qty": float(ticker['bidSz']),
                        "ask_price": float(ticker['askPx']),
                        "ask_qty": float(ticker['askSz']),
                        "last_price": float(ticker['last']),
                        "volume_24h": float(ticker['vol24h']),
                        "timestamp": datetime.fromtimestamp(int(ticker['ts'])/1000).isoformat(),
                        "price_change_24h": float(ticker['last']) - float(ticker['open24h']),
                        "price_change_percent": ((float(ticker['last']) - float(ticker['open24h'])) / float(ticker['open24h'])) * 100
                    }
                    logger.debug(f"Processed result: {result}")
                    return result
            
        except aiohttp.ClientError as e:
            logger.error(f"Network error: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Network error: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to fetch OKX price: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch OKX price: {str(e)}"
            )
            
    def _format_symbol(self, symbol: str) -> str:
        """
        将统一格式的交易对转换为OKX格式
        BTCUSDT -> BTC-USDT
        BTCJPY -> BTC-JPY
        """
        symbol = symbol.upper()
        if '-' not in symbol:
            if 'USDT' in symbol:
                base = symbol.replace('USDT', '')
                return f"{base}-USDT"
            elif 'JPY' in symbol:
                base = symbol.replace('JPY', '')
                return f"{base}-JPY"
        return symbol 