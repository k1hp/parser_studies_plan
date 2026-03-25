from src.schemas.response_schemas import ApiResponseSchema
from src.schemas.xml_schemas import DisciplineDetail
from src.services.xml_parsing_service import WebParsingService, XmlParsingService


class AnalyzeService:
    def __init__(self, web_parser_service: WebParsingService, xml_parser_service: XmlParsingService):
        self.web_parser_service = web_parser_service
        self.xml_parser_service = xml_parser_service

    def analyze_one(self, url: str, content: bytes) -> ApiResponseSchema:
        ...


    # def analyze_all(self, files: list[bytes]):
    #     web_data = self.web_parser_service.parse_url(url)
    #     web_data = self.extract_from_content(files[0])
        # xml_data = self.xml_parser_service.extract_all_files(files)

    def _compare_lists(self, correct_list: list[DisciplineDetail], checking_list: list[DisciplineDetail]) -> list[str] | list:
        return list(set(el.to_string for el in correct_list) - set(el.to_string for el in checking_list))

if __name__ == "__main__":
    service = AnalyzeService(WebParsingService(), XmlParsingService())

    ls = [DisciplineDetail(discipline_name="name", discipline_code=str(i)) for i in range(10)]
    print(ls[0].to_tuple)

    # list =
    res = service._compare_lists(ls, ls[1:3])
    print(res)






















