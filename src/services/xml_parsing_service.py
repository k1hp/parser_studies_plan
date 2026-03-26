# примеры вам, то есть конечная точка
# все по своим файлам
from src.schemas.xml_schemas import ResponseModel, DisciplineDetail
from src.schemas.web_schemas import CurriculumModel


class XmlParsingService:
    def __init__(self):
        ...

    def extract_all_files(self, contents: list[bytes]) -> list[ResponseModel]:
        ...

class WebParsingService:
    def __init__(self):
        ...

    def parse_url(self, url: str) -> CurriculumModel:
        CurriculumModel.model_validate({
            "specialty": "09.03.01 Информатика и вычислительная техника",
            "discipline_code": "09.03.01",
            "curriculum_year": "2024",
            "education_program": True,
            "lvl_education": "Бакалавриат",
            "form_education": "Очная",
            "calendar_graphic": True,
            "education_plan": True,
            "working_programs": [
                DisciplineDetail(discipline_name="Иностранный язык", discipline_code="Б1.О.03"),
                DisciplineDetail(discipline_name="Физическая культура и спорт", discipline_code="Б1.О.05"),
                DisciplineDetail(discipline_name="Русский язык и культура речи", discipline_code="Б1.О.06"),
                DisciplineDetail(discipline_name="Основы информатики", discipline_code="Б1.О.09"),
                DisciplineDetail(discipline_name="История России", discipline_code="Б1.О.02"),
                DisciplineDetail(discipline_name="Философия", discipline_code="Б1.О.01"),
                DisciplineDetail(discipline_name="Безопасность жизнедеятельности", discipline_code="Б1.О.04"),
                DisciplineDetail(discipline_name="Структуры и алгоритмы обработки данных",
                                 discipline_code="Б1.О.17.02"),
                DisciplineDetail(discipline_name="Численные методы", discipline_code="Б1.О.17.03"),
                DisciplineDetail(discipline_name="Базы данных", discipline_code="Б1.О.17.04"),
                DisciplineDetail(discipline_name="Сети ЭВМ и телекоммуникации", discipline_code="Б1.О.17.05"),
                DisciplineDetail(discipline_name="Системный анализ и принятие решений", discipline_code="Б1.О.17.08"),
                DisciplineDetail(discipline_name="Защита информации", discipline_code="Б1.О.15.02"),
                DisciplineDetail(discipline_name="Операционные системы", discipline_code="Б1.О.17.01")
            ],
            "fos_materials": [
                DisciplineDetail(discipline_name="Иностранный язык", discipline_code="Б1.О.03"),
                DisciplineDetail(discipline_name="Базы данных", discipline_code="Б1.О.17.04"),
                DisciplineDetail(discipline_name="Операционные системы", discipline_code="Б1.О.17.01")
            ],
            "practic_programs": [
                "Производственная практика, технологическая (проектно-технологическая) практика",
                "Учебная практика, ознакомительная практика"
            ],
            "methodical_materials": [
                DisciplineDetail(discipline_name="Иностранный язык", discipline_code="Б1.О.03"),
                DisciplineDetail(discipline_name="Русский язык и культура речи", discipline_code="Б1.О.06"),
                DisciplineDetail(discipline_name="Базы данных", discipline_code="Б1.О.17.04")
            ],
            "gia_program": True,
            "education_program_vosp": True,
            "curriculum_plan": True
        })