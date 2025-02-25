from fastapi import APIRouter, Depends, Query, HTTPException
from services.binance_service import BinanceService
from services.okx_service import OKXService
from services.okj_service import OKJService
from services.power_service import PowerService
from typing import Optional
from enum import Enum
from decimal import Decimal, ROUND_HALF_UP
from core.logging import logger
from services.google_service import GoogleService
from core.config import settings
import telegram
import asyncio
from telegram.constants import ParseMode
from telegram.helpers import escape_markdown
from datetime import datetime
import textwrap
import telegramify_markdown
from services.template_service import TemplateService
from services.scheduler_service import SchedulerService


class Exchange(str, Enum):
    BINANCE = "binance"
    OKX = "okx"
    OKJ = "okj"
    GOOGLE = "google"

router = APIRouter()

tg_token = settings.TG_BOT_TOKEN
gid = settings.TG_GID
tg_bot = telegram.Bot(token=tg_token)

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
    id: Optional[str] = Query(None,description="价格倍率分组Id" ),
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
        elif id:
            try:
                power_config = await power_service.get_config_by_id(id)
                power = Decimal(str(power_config.power))
                logger.info(f"Using power multiplier {power} for id {id}")
            except HTTPException as e:
                if e.status_code == 404:
                    logger.warning(f"Power config not found for group id {id}, using default power 1.0")
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

@router.get("/boardcast", summary="发送USDT/JPY组合计算价格")
async def get_compose_price_by_period():
    # 创建服务实例
    binance_service = BinanceService()
    okj_service = OKJService()
    google_service = GoogleService()
    power_service = PowerService()
    template_service = TemplateService()
    
    # 调用get_compose_price函数并打印结果
    res = await get_compose_price(
        group=None,
        binance_service=binance_service,
        okj_service=okj_service,
        google_service=google_service,
        power_service=power_service
    )
    
    bid_price = res['usdt_jpy']['bid_price']
    ask_price = res['usdt_jpy']['ask_price']
    last_price = res['usdt_jpy']['last_price']
    google_last_price = res['usdt_jpy_google']['last_price']
    time_raw = res['calculation_time']
    formatted_time = datetime.fromisoformat(time_raw.replace('Z', '+00:00')).strftime('%Y-%m-%d %H:%M:%S')
    
    # 获取消息模板
    template_data = await template_service.get_template('price_broadcast')
    template = template_data['content']
    
    # 使用模板格式化消息
    markdown_text = template.format(
        bid_price=bid_price,
        ask_price=ask_price,
        last_price=last_price,
        google_last_price=google_last_price,
        formatted_time=formatted_time
    )
    formatted_content = telegramify_markdown.markdownify(markdown_text)
    
    await tg_bot.send_message(
        chat_id=gid,
        text=formatted_content,
        parse_mode=ParseMode.MARKDOWN_V2
    )
    
    return res

@router.put("/template/{template_id}", summary="更新消息模板")
async def update_message_template(
    template_id: str,
    template_data: dict,
    template_service: TemplateService = Depends(TemplateService)
):
    """更新指定ID的消息模板
    
    参数:
        - template_id: 模板ID
        - template_data: 模板数据，包含title和content字段
    """
    return await template_service.update_template(template_id, template_data)

@router.get("/template/{template_id}", summary="获取消息模板")
async def get_message_template(
  template_id: str,
  template_service: TemplateService = Depends(TemplateService)  
):
    """获取指定ID的消息模板
    
    参数:
        - template_id: 模板ID
        
    返回:
        - 包含模板信息的字典，包括title和content字段
    """
    return await template_service.get_template(template_id)

@router.get("/broadcast-interval", summary="获取价格广播间隔配置")
async def get_broadcast_interval():
    """获取当前的价格广播间隔配置
    
    返回:
        - minutes: 当前的广播间隔（分钟）
    """
    return {"minutes": settings.PRICE_BROADCAST_INTERVAL}

@router.put("/broadcast-interval", summary="更新价格广播间隔配置")
async def update_broadcast_interval(
    minutes: int = Query(..., description="广播间隔（分钟）", gt=0)
):
    """更新价格广播间隔配置
    
    参数:
        - minutes: 新的广播间隔（分钟），必须大于0
    """
    # 更新配置
    settings.PRICE_BROADCAST_INTERVAL = minutes
    
    # 重新调度定时任务
    scheduler_service = SchedulerService()
    job = scheduler_service.get_job('price_broadcast')
    logger.info(f"jobjob: {job}")
    if job:
        scheduler_service.reschedule_job('price_broadcast','interval', minutes=minutes)
        logger.info(f"Rescheduled price broadcast job with new interval: {minutes} min(s)")
    
    return {"message": f"Successfully updated broadcast interval to {minutes} min(s)"}


    
    