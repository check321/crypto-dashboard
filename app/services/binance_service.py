from binance.client import Client
from binance.exceptions import BinanceAPIException
from fastapi import HTTPException
from datetime import datetime

class BinanceService:
    def __init__(self):
        self.client = Client()
        
    async def get_price(self, symbol: str) -> dict:
        """
        获取指定交易对的实时买卖价格
        
        Args:
            symbol: 交易对名称（例如：BTCUSDT, ETHUSDT）
        """
        try:
            symbol = symbol.upper()
            # 使用get_ticker获取更详细的价格信息
            ticker = self.client.get_ticker(symbol=symbol)
            
            return {
                "symbol": symbol,
                "bid_price": float(ticker['bidPrice']),    # 买入价
                "bid_qty": float(ticker['bidQty']),        # 买入数量
                "ask_price": float(ticker['askPrice']),    # 卖出价
                "ask_qty": float(ticker['askQty']),        # 卖出数量
                "last_price": float(ticker['lastPrice']),  # 最新成交价
                "volume": float(ticker['volume']),         # 24小时成交量
                "timestamp": datetime.fromtimestamp(ticker['closeTime']/1000).isoformat(),
                "price_change_24h": float(ticker['priceChange']),        # 24小时价格变化
                "price_change_percent": float(ticker['priceChangePercent']) # 24小时价格变化百分比
            }
        except BinanceAPIException as e:
            if e.code == -1121:  # 无效的交易对
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid symbol: {symbol}"
                )
            raise HTTPException(
                status_code=500,
                detail=f"Binance API error: {str(e)}"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch price: {str(e)}"
            ) 