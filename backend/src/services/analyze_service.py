from backend.src.schemas.response_schemas import ApiResponseSchema
from backend.src.schemas.web_schemas import CurriculumModel
from backend.src.schemas.xml_schemas import DisciplineDetail, ResponseModel
from backend.src.services.xml_parsing_service import WebParsingService, XmlParsingService
from backend.src.utils import applogger


class AnalyzeService:
    def __init__(self, web_parser_service: WebParsingService, xml_parser_service: XmlParsingService):
        self.web_parser_service = web_parser_service
        self.xml_parser_service = xml_parser_service
    # 1. общая функция анализа
    def _compare_models(self, web_object: CurriculumModel, xml_object: ResponseModel) -> ApiResponseSchema:
        result: dict = {}

        for key, value in web_object.model_dump().items():
            if key == "speciality" and value == xml_object.direction_name:
                result[key] = value
            elif key == "discipline_code" and value == xml_object.direction_code:
                result[key] = value
            elif isinstance(value, list) and len(value) > 0 and isinstance(value[0], DisciplineDetail):
                result[key] = self._compare_lists(xml_object.disciplines, value)

            else:
                result[key] = value
                # raise ValueError(f"Unexpected value {value} of {key}")
        return ApiResponseSchema.model_validate(result)

    # 2. анализ одной и получение нужного года
    def analyze_one(self, url: str, content: bytes) -> ApiResponseSchema:
        web_data = self.web_parser_service.parse_url(url)
        applogger.debug("web data", web_data)
        xml_data = self.xml_parser_service.extract_from_content(content)
        return self._compare_models(web_data, xml_data)



    # 3. по соответствию года сразу пачку
    # def analyze_all(self, files: list[bytes]):
    #     web_data = self.web_parser_service.parse_url(url)
    #     web_data = self.extract_from_content(files[0])
        # xml_data = self.xml_parser_service.extract_all_files(files)

    def _compare_lists(self, correct_list: list[DisciplineDetail], checking_list: list[DisciplineDetail]) -> list[str] | list:
        result_list: list[str] = []
        for correct, check in zip(correct_list, checking_list):
            if correct.discipline_code != check.discipline_code:
                result_list.append(correct.to_string)
            if correct.discipline_name not in "".join(el.to_string for el in checking_list):
                result_list.append(correct.to_string)

        return result_list

if __name__ == "__main__":
    service = AnalyzeService(WebParsingService(), XmlParsingService())

    xml = [DisciplineDetail(discipline_name="name1", discipline_code=str(i)) for i in range(10)]
    ls3 = [DisciplineDetail(discipline_name="name_MM", discipline_code=str(i)) for i in range(10)]

    print(xml[0].to_tuple)

    # list =
    res = service._compare_lists(xml, ls3)
    print(res)






















