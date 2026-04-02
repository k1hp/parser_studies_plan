from pydantic import BaseModel, Field

from backend.src.schemas.xml_schemas import DisciplineDetail


class CurriculumModel(BaseModel):
    specialty: str = Field(..., description="Название специальности")
    discipline_code: str = Field(..., description="Код дисциплины")
    curriculum_year: str = Field(..., description="Год набора")
    education_program: bool = Field(..., description="Наличие раздела 'Образовательная программа'")
    lvl_education: str = Field(..., description="Уровень образования")
    form_education: str = Field(..., description="Форма обучения")
    calendar_graphic: bool = Field(..., description="Наличие календарного учебного графика")
    education_plan: bool = Field(..., description="Наличие учебного плана")

    working_programs: list[DisciplineDetail] = Field(default=[], description="Список рабочих программ дисциплин")
    fos_materials: list[DisciplineDetail] = Field(default=[], description="Список ФОС материалов")
    practic_programs: list[str] = Field(default=[], description="Список программ практик (не сравниваем)")
    methodical_materials: list[DisciplineDetail] = Field(default=[], description="Список методических материалов")

    gia_program: bool = Field(..., description="Наличие раздела 'ГИА'")
    education_program_vosp: bool = Field(..., description="Наличие раздела 'Рабочая программа воспитания'")
    curriculum_plan: bool = Field(..., description="Наличие Календарного плана воспитательной работы")