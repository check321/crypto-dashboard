import json
import os
from fastapi import HTTPException
from models.power import PowerConfig
from typing import List
import aiofiles
from core.logging import logger
from pathlib import Path
import random,string

class PowerService:
    def __init__(self):
        # 获取项目根目录
        root_dir = Path(__file__).parent.parent.parent
        # 设置配置文件路径
        self.config_file = os.path.join(root_dir,"g-power.json")
        logger.info(f"Power service config file path: {self.config_file}")
        self._ensure_config_file()
       
    
    def _ensure_config_file(self):
        """确保配置文件存在"""
        if not os.path.exists(self.config_file):
            with open(self.config_file, 'w') as f:
                json.dump({"configs": []}, f)
    
    async def _read_config(self) -> dict:
        """读取配置文件"""
        try:
            async with aiofiles.open(self.config_file, 'r') as f:
                content = await f.read()
                return json.loads(content)
        except Exception as e:
            logger.error(f"Failed to read config file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to read configuration"
            )
    
    async def _write_config(self, data: dict):
        """写入配置文件"""
        try:
            async with aiofiles.open(self.config_file, 'w') as f:
                await f.write(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to write config file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Failed to write configuration"
            )
    
    async def get_all_configs(self) -> List[PowerConfig]:
        """获取所有配置"""
        data = await self._read_config()
        return [PowerConfig(**config) for config in data.get("configs", [])]
    
    async def get_config_by_group(self, group: str) -> PowerConfig:
        """根据组名获取配置"""
        configs = await self.get_all_configs()
        for config in configs:
            if config.group == group:
                return config
        raise HTTPException(
            status_code=404,
            detail=f"Configuration not found for group: {group}"
        )
    
    async def get_config_by_id(self, id: str) -> PowerConfig:
        """根据id获取配置"""
        configs = await self.get_all_configs()
        for config in configs:
            if config.id == id:
                return config
        raise HTTPException(
            status_code=404,
            detail=f"Configuration not found for id: {id}"
        )
        
    
    async def create_config(self, config: PowerConfig) -> PowerConfig:
        """创建新配置"""
        data = await self._read_config()
        configs = data.get("configs", [])
        
        # 检查是否已存在
        if any(c["group"] == config.group for c in configs):
            raise HTTPException(
                status_code=400,
                detail=f"Configuration already exists for group: {config.group}"
            )
        
        # new_id = max([c.get("id", 0) for c in configs], default=0) + 1
        # crate a 6-character random ID made up of both number and letters.
        new_id = self._generate_random_id()
        config_dict = config.dict()
        config_dict["id"] = new_id
        
        configs.append(config_dict)
        data["configs"] = configs
        await self._write_config(data)
        
        return PowerConfig(**config_dict)
    
    def _generate_random_id(self) -> str:
        characters = string.ascii_letters + string.digits
        return ''.join(random.choices(characters,k=6))
    
    async def update_config(self, group: str, config: PowerConfig) -> PowerConfig:
        """更新配置"""
        data = await self._read_config()
        configs = data.get("configs", [])
        
        for i, existing_config in enumerate(configs):
            if existing_config["group"] == group:
                config_dict = config.dict(exclude_unset=True)
                config_dict["id"] = existing_config["id"]
                config_dict["group"] = group
                configs[i] = config_dict
                data["configs"] = configs
                await self._write_config(data)
                return PowerConfig(**config_dict)
                
        raise HTTPException(
            status_code=404,
            detail=f"Configuration not found for group: {group}"
        )
    
    async def delete_config(self, group: str):
        """删除配置"""
        data = await self._read_config()
        configs = data.get("configs", [])
        
        filtered_configs = [c for c in configs if c["group"] != group]
        if len(filtered_configs) == len(configs):
            raise HTTPException(
                status_code=404,
                detail=f"Configuration not found for group: {group}"
            )
            
        data["configs"] = filtered_configs
        await self._write_config(data) 
    
    async def update_all_powers(self, power: float) -> List[PowerConfig]:
        """
        更新所有配置的power值
        
        Args:
            power: 新的power值
        """
        try:
            data = await self._read_config()
            configs = data.get("configs", [])
            
            if not configs:
                raise HTTPException(
                    status_code=404,
                    detail="No configurations found"
                )
            
            # 更新所有配置的power值
            for config in configs:
                config["power"] = power
                
            data["configs"] = configs
            await self._write_config(data)
            
            logger.info(f"Updated power to {power} for {len(configs)} configurations")
            return [PowerConfig(**config) for config in configs]
            
        except Exception as e:
            logger.error(f"Failed to update all powers: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update powers: {str(e)}"
            ) 