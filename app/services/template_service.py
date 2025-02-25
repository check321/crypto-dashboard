import json
from pathlib import Path
from fastapi import HTTPException
from core.logging import logger

class TemplateService:
    def __init__(self):
        self.template_file = Path(__file__).parent.parent / 'templates' / 'message_template.json'
        
    async def get_template(self, template_id: str) -> dict:
        """获取指定ID的模板"""
        try:
            if not self.template_file.exists():
                raise HTTPException(
                    status_code=404,
                    detail="Template file not found"
                )
                
            with open(self.template_file, 'r', encoding='utf-8') as f:
                templates = json.load(f)
                
            if template_id not in templates:
                raise HTTPException(
                    status_code=404,
                    detail=f"Template {template_id} not found"
                )
                
            return templates[template_id]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse template file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Invalid template file format"
            )
        except Exception as e:
            logger.error(f"Failed to read template: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read template: {str(e)}"
            )
    
    async def update_template(self, template_id: str, template_data: dict) -> dict:
        """更新指定ID的模板"""
        try:
            if not self.template_file.exists():
                raise HTTPException(
                    status_code=404,
                    detail="Template file not found"
                )
                
            with open(self.template_file, 'r', encoding='utf-8') as f:
                templates = json.load(f)
                
            if template_id not in templates:
                raise HTTPException(
                    status_code=404,
                    detail=f"Template {template_id} not found"
                )
            # update_data = template_data["template_data"]    
            templates[template_id].update(template_data)
            
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, ensure_ascii=False, indent=4)
                
            return templates[template_id]
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse template file: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail="Invalid template file format"
            )
        except Exception as e:
            logger.error(f"Failed to update template: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update template: {str(e)}"
            )