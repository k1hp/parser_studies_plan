from datetime import datetime
import os
import xml.etree.ElementTree as ET
import re

from sentry_sdk.utils import capture_internal_exception

from backend.src.utils import applogger
from backend.src.schemas.xml_schemas import ResponseModel, DisciplineDetail
from backend.src.schemas.web_schemas import CurriculumModel
# from src.models.response_model_xml_parser import ResponseModel, DisciplineDetail
from backend.src.services.file_manager import FileManager
from backend.src.services.pdf_service import PDFService

class PlxDataExtractor:

    @staticmethod
    def extract_direction_code(root: ET.Element) -> str:
        try:
            for elem in root.iter():
                if elem.tag.endswith('ООП'):
                    code = elem.get('Шифр', '')
                    if code:
                        return code.strip()
        except Exception as e:
            applogger.error(f"Ошибка при извлечении кода направления: {e}")
        return ""

    @staticmethod
    def extract_direction_name(root: ET.Element) -> tuple[str, str]:
        direction_name = ""
        profile_name = ""

        try:
            for elem in root.iter():
                if elem.tag.endswith('ООП'):
                    parent_code = elem.get('КодРодительскогоООП', '')
                    if not parent_code:
                        direction_name = elem.get('Название', '')

                    else:
                        profile_name = elem.get('Название', '')

        except Exception as e:
            applogger.error(f"Ошибка при извлечении названия направления: {e}")
        return direction_name.strip(), profile_name.strip()

    @staticmethod
    def extract_start_year(root: ET.Element) -> int:
        try:
            for elem in root.iter():
                if elem.tag.endswith('Планы'):
                    year_value = elem.get('ГодНачалаПодготовки', '')
                    if year_value and year_value.strip():
                        try:
                            return int(year_value.strip())
                        except ValueError:
                            match = re.search(r'\b(20\d{2})\b', year_value)
                            if match:
                                return int(match.group(1))

        except Exception as e:
            applogger.error(f"Ошибка при извлечении года начала обучения: {e}")

        return datetime.now().year

    @staticmethod
    def extract_disciplines_details(root: ET.Element) -> list[DisciplineDetail]:
        unique_disciplines = []

        try:
            seen = set()
            for elem in root.iter():
                if elem.tag.endswith('ПланыСтроки'):
                    name = elem.get('Дисциплина', '').strip()
                    code = elem.get('ДисциплинаКод', '').strip() or None

                    if not name or not name:
                        continue

                    if (name, code) not in seen:
                        seen.add((name, code))

                        discipline = DisciplineDetail(
                            discipline_name=name,
                            discipline_code=code,
                        )
                        unique_disciplines.append(discipline)

            return unique_disciplines

        except Exception as e:
            applogger.error(f"Ошибка при извлечении информации о дисциплинах: {e}")
            return []

class XmlParsingService:

    def __init__(self, pdf_service: PDFService):
        self._pdf_service = pdf_service
        self._root = None

    def _parse_xml(self, content: bytes) -> ET.Element | None:
        if not content:
            return None
        try:
            try:
                xml_str = content.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    xml_str = content.decode('utf-16')
                except UnicodeDecodeError:
                    xml_str = content.decode('windows-1251')

            self._root = ET.fromstring(xml_str)
            return self._root

        except ET.ParseError as e:
            applogger.error(f"Ошибка парсинга XML: {e}")
            return None
        except Exception as e:
            applogger.error(f"Неожиданная ошибка при парсинге: {e}")
            return None

    def extract_all(self, contents: list[bytes]) -> list[ResponseModel]:
        results = []

        for content in contents:
            response = self.extract_from_content(content)
            results.append(response)

        return results

    def extract_from_content(self, content: bytes) -> ResponseModel | None:
        root = self._parse_xml(content)

        if root is None:
            applogger.warning("Не удалось извлечь root из контента (XML/PLX пустой).")
            return None

        direction_code = PlxDataExtractor.extract_direction_code(root)
        direction_name, profile_name = PlxDataExtractor.extract_direction_name(root)
        start_year = PlxDataExtractor.extract_start_year(root)
        disciplines = PlxDataExtractor.extract_disciplines_details(root)

        full_direction_name = f"{direction_name}, {profile_name}" if profile_name else direction_name

        return ResponseModel(
            direction_code=direction_code,
            direction_name=full_direction_name,
            start_year=start_year,
            disciplines=disciplines
        )

class WebParsingService:
    def __init__(self):
        ...

    def parse_url(self, url: str) -> CurriculumModel:
        return CurriculumModel.model_validate({
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



if __name__ == "__main__":
    pdf_service = PDFService(template_dir="templates")
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.abspath(os.path.join(current_script_dir, "..", "directory"))
    file_manager = FileManager(folder_path)
    extractor = XmlParsingService(pdf_service=pdf_service)
    files = file_manager.get_files_in_directory()
    contents = file_manager.get_files_contents(files)
    extracted_items = extractor.extract_all(contents)

    if files:
        for file_path in files:
            content = file_manager.get_files_contents([file_path])[0]

            response = extractor.extract_from_content(content)

            if response:
                base_name = os.path.splitext(os.path.basename(file_path))[0]

                pdf_file_name = f"report_{base_name}.pdf"

                pdf_bytes = pdf_service.create_pdf(response)
                with open(pdf_file_name, "wb") as f:
                    f.write(pdf_bytes)

                applogger.info(f"PDF сохранен: {pdf_file_name} (из файла {file_path})")

            #applogger.debug("\nJSON представление:")
            #applogger.debug(response.model_dump_json(indent=2, ensure_ascii=False))

        #pdf_content = pdf_service.create_pdf(extracted_items)

    else:
        applogger.info(f"Файлы не найдены в директории: {folder_path}")