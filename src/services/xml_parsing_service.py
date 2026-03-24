from typing import List
from datetime import datetime
import os
import xml.etree.ElementTree as ET
import re
from models.response_model_xml_parser import ResponseModel, DisciplineDetail


class FileManager:

    def __init__(self, folder_path: str):
        self.directory = folder_path
        self.file_path = ""

    def read_file_content(self) -> bytes:
        if not self.file_path:
            return b""
        with open(self.file_path, 'rb') as f:
            return f.read()

    # Функция для получения всех файлов из папки с указанным расширением (пока что из папки directory на уровне выше)
    def get_files_in_directory(self, extension: str = ".xml" or ".plx") -> List[str]:
        if not os.path.exists(self.directory):
            print(f"Ошибка: директории {self.directory} не существует!")
            return []

        return [
            os.path.join(self.directory, f)
            for f in os.listdir(self.directory)
            if f.endswith(extension)
        ]

    def set_current_file(self, path: str):
        self.file_path = path


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
            print(f"Ошибка при извлечении кода направления: {e}")
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
            print(f"Ошибка при извлечении названия направления: {e}")
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
            print(f"Ошибка при извлечении года начала обучения: {e}")

        return datetime.now().year

    @staticmethod
    def extract_disciplines_details(root: ET.Element) -> List[DisciplineDetail]:
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
            print(f"Ошибка при извлечении информации о дисциплинах: {e}")
            return []


class XmlParsingService:

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
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
            print(f"Ошибка парсинга XML: {e}")
            return None
        except Exception as e:
            print(f"Неожиданная ошибка при парсинге: {e}")
            return None

    def extract_all_files(self) -> List[ResponseModel]:
        results = []
        files = self.file_manager.get_files_in_directory(extension='.plx' or '.xml')

        for file_path in files:
            self.file_manager.set_current_file(file_path)
            response = self.extract_response_data()
            file_name = os.path.basename(file_path)
            self.print_response(response, file_name)
            results.append(response)

        return results

    # Это функция для работы JSON представления, без неё не работает
    def extract_all_with_paths(self) -> list[tuple[ResponseModel, str]]:
        results = []
        files = self.file_manager.get_files_in_directory(extension='.plx' or '.xml')

        for file_path in files:
            self.file_manager.set_current_file(file_path)
            response = self.extract_response_data()
            results.append((response, file_path))

        return results


    def extract_response_data(self) -> ResponseModel:
        content = self.file_manager.read_file_content()
        root = self._parse_xml(content)

        if root is None:
            current_year = datetime.now().year
            return ResponseModel(
                direction_code="",
                direction_name="",
                start_year=current_year,
                disciplines=[]
            )

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

    def print_response(self, response: ResponseModel, file_name: str) -> None:
        print("=" * 120)
        print(f"РЕЗУЛЬТАТ ПАРСИНГА ФАЙЛА: {file_name}")
        print("=" * 120)
        print(f"\nКод направления: {response.direction_code}")
        print(f"Название направления: {response.direction_name}")
        print(f"Год начала обучения: {response.start_year}")
        print(f"\nСПИСОК ДИСЦИПЛИН (всего: {len(response.disciplines)}):")
        print("=" * 120)

        if response.disciplines:
            for i, disc in enumerate(response.disciplines, 1):
                print(f"\n{i}. {disc.discipline_name}")
                print(f"   Код дисциплины: {disc.discipline_code or 'Не указан'}")
                print("-" * 100)
        else:
            print("\n  Дисциплины не найдены")

        print("=" * 120)


if __name__ == "__main__":
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = os.path.abspath(os.path.join(current_script_dir, "..", "directory")) # Вероятно, нужно будет изменить в будущем путь к папке
    file_manager = FileManager(folder_path)
    extractor = XmlParsingService(file_manager)
    extracted_items = extractor.extract_all_with_paths()

    if extracted_items:
        for response, file_path in extracted_items:
            file_name = os.path.basename(file_path)
            extractor.print_response(response, file_name)

            print("\nJSON представление:")
            print(response.model_dump_json(indent=2, ensure_ascii=False))

    else:
        print(f"Файлы не найдены в директории: {folder_path}")