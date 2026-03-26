from datetime import datetime
import os
import xml.etree.ElementTree as ET
import re
from utils import applogger
from models.response_model_xml_parser import ResponseModel, DisciplineDetail
from services.file_manager import FileManager

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
    def extract_direction_name(root: ET.Element) -> str:
        try:
            for elem in root.iter():
                if elem.tag.endswith('ООП'):
                    name = elem.get('Название', '')
                    if name:
                        return name.strip()
        except Exception as e:
            applogger.error(f"Ошибка при извлечении названия направления: {e}")
        return ""

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

    def __init__(self, file_manager: FileManager):
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
            applogger.warning("Не удалось извлечь root из контента (XML/PLX пустой или некорректный).")
            return None

        direction_code = PlxDataExtractor.extract_direction_code(root)
        direction_name = PlxDataExtractor.extract_direction_name(root)
        start_year = PlxDataExtractor.extract_start_year(root)
        disciplines = PlxDataExtractor.extract_disciplines_details(root)

        return ResponseModel(
            direction_code=direction_code,
            direction_name=direction_name,
            start_year=start_year,
            disciplines=disciplines
        )


if __name__ == "__main__":
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.abspath(os.path.join(current_script_dir, "..", "directory"))
    file_manager = FileManager(folder_path)
    extractor = XmlParsingService(file_manager)
    files = file_manager.get_files_in_directory()
    contents = file_manager.get_files_contents(files)
    extracted_items = extractor.extract_all(contents)

    if extracted_items:
        for response in extracted_items:

            applogger.debug("\nJSON представление:")
            applogger.debug(response.model_dump_json(indent=2, ensure_ascii=False))

    else:
        applogger.info(f"Файлы не найдены в директории: {folder_path}")