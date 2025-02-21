from pydantic import BaseModel
from typing import Optional

class PowerConfig(BaseModel):
    id: str = None
    group: str
    power: float = 1.0
    description: Optional[str] = None 