from multipart import file_path
import os
from backend.src.schemas.response_schemas import ApiResponseSchema
from backend.src.schemas.web_schemas import CurriculumModel
from backend.src.schemas.xml_schemas import DisciplineDetail, ResponseModel
from backend.src.services.pdf_service import PDFService
from backend.src.services.xml_parsing_service import WebParsingService, XmlParsingService
from backend.src.utils import applogger


class AnalyzeService:
    def __init__(self, web_parser_service: WebParsingService, xml_parser_service: XmlParsingService, pdf_service, file_manager: None):
        self.web_parser_service = web_parser_service
        self.xml_parser_service = xml_parser_service
        self.pdf_service = pdf_service
        self.file_manager = file_manager

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

    # 2. анализ одной и получение нужного года (использовать эту функцию для pdf конвертера, создания отчета) (чтобы ApiResponseSchema переконвертировалась в pdf)
    def analyze_one(self, url: str, file_path: str, content: bytes = None) -> ApiResponseSchema:
        if file_path and self.file_manager:
            content = self.file_manager.get_one_content(file_path)
        elif not content:
            raise ValueError("Необходимо передать либо file_path, либо content")

        web_data = self.web_parser_service.parse_url(url)
        xml_data = self.xml_parser_service.extract_from_content(content)
        return self._compare_models(web_data, xml_data)

    def analyze_one_and_create_report(self, url: str, file_path: str, output_pdf_path: str = None) -> bytes:
        result = self.analyze_one(url, file_path)

        if output_pdf_path:
            pdf_bytes = self.pdf_service.create_pdf(result, output_path=output_pdf_path)
        else:
            pdf_bytes = self.pdf_service.create_pdf(result)

        return pdf_bytes


    # 3. по соответствию года сразу пачку
    # def analyze_all(self, files: list[bytes]):
    #     web_data = self.web_parser_service.parse_url(url)
    #     web_data = self.extract_from_content(files[0])
        # xml_data = self.xml_parser_service.extract_all_files(files)

    def _compare_lists(self, correct_list: list[DisciplineDetail], checking_list: list[DisciplineDetail]) -> list[DisciplineDetail] | list:
        result_list: list[str] = []
        for check in checking_list:
            flag = False
            for correct in correct_list:
                if correct.discipline_code == check.discipline_code:
                    flag = True

            if not flag:
                result_list.append(correct)

        return result_list

if __name__ == "__main__":
    from backend.src.services.file_manager import FileManager

    pdf_service = PDFService(template_dir="templates")
    file_manager = FileManager(file_path)

    service = AnalyzeService(
        WebParsingService(),
        XmlParsingService(pdf_service=pdf_service),
        PDFService(),
        file_manager=file_manager
    )

    xml = [DisciplineDetail(discipline_name="name1", discipline_code=str(i)) for i in range(10)]
    ls3 = [DisciplineDetail(discipline_name="name_MM", discipline_code=str(i)) for i in range(10)]

    print(xml[0].to_tuple)

    res = service._compare_lists(xml, ls3)
    print(res)

    target_url = WebParsingService().parse_url
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.abspath(os.path.join(current_script_dir, "..", "directory", "example.plx"))
    try:
        analytic_results = service.analyze_one(target_url, file_path)
        pdf_bytes = service.pdf_service.create_pdf(analytic_results, 'report.pdf')
    except Exception as e:
        applogger.error(f"Произошла ошибка: {e}")
    #result = service.analyze_one(url, file_path=file_path))
    #pdf_bytes = service.analyze_one_and_create_report(url, file_path, "output/report.pdf")






















