from fastapi import APIRouter, Depends, HTTPException, Body
from models.power import PowerConfig
from services.power_service import PowerService
from typing import List
from core.logging import logger
from pydantic import BaseModel

router = APIRouter()

# 添加请求体模型
class PowerUpdate(BaseModel):
    power: float

@router.get("/configs", response_model=List[PowerConfig])
async def get_all_configs(
    power_service: PowerService = Depends(PowerService)
):
    """获取所有价格计算倍数配置"""
    return await power_service.get_all_configs()

@router.get("/configs/{group}", response_model=PowerConfig)
async def get_config(
    group: str,
    power_service: PowerService = Depends(PowerService)
):
    """获取指定组的价格计算倍数配置"""
    return await power_service.get_config_by_group(group)

@router.post("/configs", response_model=PowerConfig)
async def create_config(
    config: PowerConfig,
    power_service: PowerService = Depends(PowerService)
):
    """创建新的价格计算倍数配置"""
    return await power_service.create_config(config)

@router.put("/configs/{group}", response_model=PowerConfig)
async def update_config(
    group: str,
    config: PowerConfig,
    power_service: PowerService = Depends(PowerService)
):
    """更新指定组的价格计算倍数配置"""
    return await power_service.update_config(group, config)

@router.delete("/configs/{group}")
async def delete_config(
    group: str,
    power_service: PowerService = Depends(PowerService)
):
    """删除指定组的价格计算倍数配置"""
    await power_service.delete_config(group)
    return {"message": "Configuration deleted successfully"}

@router.put("/configs/power/batch", response_model=List[PowerConfig], summary="批量更新所有配置的power值")
async def update_all_powers(
    power_update: PowerUpdate,  # 使用Pydantic模型作为请求体
    power_service: PowerService = Depends(PowerService)
):
    """
    批量更新所有配置组的power值
    
    参数:
        - power: 新的power值（必须大于等于0）
    
    返回:
        - 更新后的所有配置列表
    """
    try:
        return await power_service.update_all_powers(power_update.power)
    except Exception as e:
        logger.error(f"Failed to update powers: {str(e)}")
        raise 