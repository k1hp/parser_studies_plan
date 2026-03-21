from pydantic import BaseModel, Field
from typing import List, Optional


class DisciplineDetail(BaseModel):
    """Детальная информация о дисциплине"""
    name: str = Field(..., description="Название дисциплины")
    code: str = Field(..., description="Код дисциплины (ДисциплинаКод)")
    hours: Optional[str] = Field(None, description="Количество часов (ЧасовПоПлану)")
    credits: Optional[str] = Field(None, description="Трудоемкость в кредитах (ТрудоемкостьКредитов)")
    department_code: Optional[str] = Field(None, description="Код кафедры (КодКафедры)")
    semester: Optional[str] = Field(None, description="Номер семестра")
    order: Optional[str] = Field(None, description="Порядковый номер")
    object_type: Optional[str] = Field(None, description="Тип объекта (ТипОбъекта)")
    object_view: Optional[str] = Field(None, description="Вид объекта (ВидОбъекта)")
    actual_credits: Optional[str] = Field(None, description="Фактически ЗЕТ (ЗЕТфакт)")
    actual_hours: Optional[str] = Field(None, description="Фактически часов (ЧасовПоЗЕТ)")
    hours_per_credit: Optional[str] = Field(None, description="Часов в ЗЕТ (ЧасовВЗЕТ)")

class ResponseModel(BaseModel):
    """Модель ответа парсера PLX файлов"""
    direction_code: str = Field(..., description="Код направления (шифр)")
    direction_name: str = Field(..., description="Название направления")
    start_year: int = Field(..., description="Год начала обучения")
    academic_year: str = Field(..., description="Учебный год текущего курса")
    disciplines: List[DisciplineDetail] = Field(..., description="Детальный список дисциплин")