from pydantic import BaseModel, Field

class DisciplineDetail(BaseModel):
    discipline_name: str = Field(..., description="Название дисциплины")
    discipline_code: str = Field(..., description="Код дисциплины (ДисциплинаКод)")

class ResponseModel(BaseModel):
    direction_code: str = Field(..., description="Код направления (шифр)")
    direction_name: str = Field(..., description="Название направления")
    start_year: int = Field(..., description="Год начала обучения")
    disciplines: list[DisciplineDetail] = Field(..., description="Список дисциплин")