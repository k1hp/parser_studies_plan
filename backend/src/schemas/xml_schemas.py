
from pydantic import BaseModel, Field, computed_field


class DisciplineDetail(BaseModel):
    discipline_name: str = Field(..., description="Название дисциплины")
    discipline_code: str = Field(..., description="Код дисциплины (ДисциплинаКод)")

    @computed_field
    def to_tuple(self) -> tuple[str, str]:
        return (self.discipline_name, self.discipline_code)

    @computed_field
    def to_string(self) -> str:
        return f"{self.discipline_name} {self.discipline_code}"

class ResponseModel(BaseModel):
    direction_code: str = Field(..., description="Код направления (шифр)")
    direction_name: str = Field(..., description="Название направления")
    start_year: int = Field(..., description="Год начала обучения")
    disciplines: list[DisciplineDetail] = Field(..., description="Список дисциплин")