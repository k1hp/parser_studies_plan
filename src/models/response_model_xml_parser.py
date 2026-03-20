from pydantic import BaseModel, Field
from typing import List, Optional


class ResponseModel(BaseModel):
    """Модель ответа парсера PLX файлов"""
    direction_code: str = Field(..., description="Код направления (шифр)")
    direction_name: str = Field(..., description="Название направления")
    start_year: int = Field(..., description="Год начала обучения")
    academic_year: str = Field(..., description="Учебный год текущего курса")
    disciplines: List[str] = Field(..., description="Список названий дисциплин")