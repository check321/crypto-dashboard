from fastapi import APIRouter, Depends, Query, HTTPException
from services.binance_service import BinanceService
from services.okx_service import OKXService
from services.okj_service import OKJService
from services.power_service import PowerService
from typing import Optional, Literal
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
from core.logging import logger
from services.google_service import GoogleService

class Exchange(str, Enum):
    BINANCE = "binance"
    OKX = "okx"
    OKJ = "okj"
    GOOGLE = "google"

router = APIRouter()

@router.get("/price", summary="获取加密货币实时买卖价格")
async def get_crypto_price(
    symbol: str = Query(
        default="BTCUSDT",
        description="交易对名称",
        example="BTCUSDT",
        min_length=2,
        max_length=20
    ),
    exchange: Exchange = Query(
        default=Exchange.BINANCE,
        description="交易所或数据源"
    ),
    binance_service: BinanceService = Depends(BinanceService),
    okx_service: OKXService = Depends(OKXService),
    okj_service: OKJService = Depends(OKJService),
    google_service: GoogleService = Depends(GoogleService)
):
    """
    获取指定交易对的实时价格
    
    参数:
        - symbol: 交易对名称，例如 BTC/JPY, ETH/USDT
        - exchange: 数据源选择 (binance, okx, okj, google)
    """
    if exchange == Exchange.BINANCE:
        return await binance_service.get_price(symbol)
    elif exchange == Exchange.OKX:
        return await okx_service.get_price(symbol)
    elif exchange == Exchange.OKJ:
        return await okj_service.get_price(symbol)
    else:
        return await google_service.get_price(symbol)

@router.get("/compose", summary="获取USDT/JPY组合计算价格")
async def get_compose_price(
    group: Optional[str] = Query(None, description="价格倍率分组"),
    binance_service: BinanceService = Depends(BinanceService),
    okj_service: OKJService = Depends(OKJService),
    google_service: GoogleService = Depends(GoogleService),
    power_service: PowerService = Depends(PowerService)
):
    """
    通过BTC价格计算USDT/JPY汇率，支持价格倍率调整
    
    参数:
    - group: 可选，价格倍率分组名称
    """
    try:
        # 获取power倍率
        power = Decimal('1.0')
        if group:
            try:
                power_config = await power_service.get_config_by_group(group)
                power = Decimal(str(power_config.power))
                logger.info(f"Using power multiplier {power} for group {group}")
            except HTTPException as e:
                if e.status_code == 404:
                    logger.warning(f"Power config not found for group {group}, using default power 1.0")
                else:
                    raise
        
        # 并行获取所有价格数据
        btc_usdt_data = await binance_service.get_price("BTCUSDT")
        btc_jpy_data = await okj_service.get_price("BTCJPY")
        btc_jpy_google_data = await google_service.get_price("BTC/JPY")
        
        # 转换为Decimal并应用倍率
        btc_usdt = {
            'bid': Decimal(str(btc_usdt_data['bid_price'])) * power,
            'ask': Decimal(str(btc_usdt_data['ask_price'])) * power,
            'last': Decimal(str(btc_usdt_data['last_price'])) * power,
            'change_percent': Decimal(str(btc_usdt_data['price_change_percent']))
        }
        
        btc_jpy = {
            'bid': Decimal(str(btc_jpy_data['bid_price'])) * power,
            'ask': Decimal(str(btc_jpy_data['ask_price'])) * power,
            'last': Decimal(str(btc_jpy_data['last_price'])) * power,
            'change_percent': Decimal(str(btc_jpy_data['price_change_percent']))
        }
        
        btc_jpy_google = {
            'last': Decimal(str(btc_jpy_google_data['last_price'])) * power
        }
        
        # 计算USDT/JPY的买卖价格（使用OKJ数据）
        usdt_jpy = {
            'bid': (btc_jpy['bid'] / btc_usdt['ask']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'ask': (btc_jpy['ask'] / btc_usdt['bid']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
            'last': (btc_jpy['last'] / btc_usdt['last']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
        
        # 计算使用Google数据的USDT/JPY价格
        usdt_jpy_google = {
            'last': (btc_jpy_google['last'] / btc_usdt['last']).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        }
        
        # 计算买卖价差
        spread = ((usdt_jpy['ask'] - usdt_jpy['bid']) / usdt_jpy['bid'] * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        
        return {
            "usdt_jpy": {
                "bid_price": float(usdt_jpy['bid']),
                "ask_price": float(usdt_jpy['ask']),
                "last_price": float(usdt_jpy['last']),
                "spread_percent": float(spread)
            },
            "usdt_jpy_google": {
                "last_price": float(usdt_jpy_google['last'])
            },
            "source_data": {
                "btc_usdt": {
                    "bid_price": float(btc_usdt['bid']),
                    "ask_price": float(btc_usdt['ask']),
                    "last_price": float(btc_usdt['last']),
                    "change_percent_24h": float(btc_usdt['change_percent']),
                    "exchange": "Binance",
                    "timestamp": btc_usdt_data['timestamp']
                },
                "btc_jpy": {
                    "bid_price": float(btc_jpy['bid']),
                    "ask_price": float(btc_jpy['ask']),
                    "last_price": float(btc_jpy['last']),
                    "change_percent_24h": float(btc_jpy['change_percent']),
                    "exchange": "OKJ",
                    "timestamp": btc_jpy_data['timestamp']
                },
                "btc_jpy_google": {
                    "last_price": float(btc_jpy_google['last']),
                    "exchange": "Google",
                    "timestamp": btc_jpy_google_data['timestamp']
                }
            },
            "calculation_time": btc_usdt_data['timestamp'],
            "power_multiplier": float(power)
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate USDT/JPY rate: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate USDT/JPY rate: {str(e)}"
        ) 