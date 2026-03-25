# примеры вам, то есть конечная точка
# все по своим файлам
from src.schemas.xml_schemas import ResponseModel
from src.schemas.web_schemas import CurriculumModel


class XmlParsingService:
    def __init__(self):
        ...

    def extract_all_files(self, contents: list[bytes]) -> list[ResponseModel]:
        ...

class WebParsingService:
    def __init__(self):
        ...

    def parse_url(self, url: str) -> list[CurriculumModel]:
        ...