from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import os
import xml.etree.ElementTree as ET
import re
from models.response_model_xml_parser import ResponseModel


class FileManager:
    """Класс для управления файлами"""

    def __init__(self, file_path: Union[Path, str]):
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path
        self._file_content = None

    def read_file_content(self) -> bytes:
        """Чтение всего содержимого файла в байтах"""
        try:
            with open(self.file_path, 'rb') as f:
                self._file_content = f.read()
            return self._file_content
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return b""


class PlxDataExtractor:
    """Класс для извлечения данных из PLX файлов"""

    @staticmethod
    def extract_direction_code(root: ET.Element) -> str:
        """Извлечение кода направления (шифр)"""
        try:
            # Ищем элемент ООП с шифром
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
        """Извлечение названия направления"""
        try:
            # Ищем элемент ООП с названием
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
        """Извлечение года начала обучения из атрибута ГодНачалаПодготовки"""
        try:
            # Ищем в элементе Планы атрибут ГодНачалаПодготовки
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

        # Если не нашли, возвращаем текущий год
        return datetime.now().year

    @staticmethod
    def extract_academic_year(root: ET.Element) -> str:
        """Извлечение учебного года из атрибута УчебныйГод"""
        try:
            # Ищем в элементе Планы атрибут УчебныйГод
            for elem in root.iter():
                if elem.tag.endswith('Планы'):
                    year_value = elem.get('УчебныйГод', '')
                    if year_value and year_value.strip():
                        return year_value.strip()

            # Если не нашли в Планы, ищем в других элементах
            for elem in root.iter():
                for attr_name in ['УчебныйГод', 'AcademicYear', 'StudyYear']:
                    if attr_name in elem.attrib:
                        year_value = elem.get(attr_name, '')
                        if year_value and year_value.strip():
                            return year_value.strip()

        except Exception as e:
            print(f"Ошибка при извлечении учебного года: {e}")

        # Если не нашли, возвращаем строку с текущим годом
        current_year = datetime.now().year
        return f"{current_year}-{current_year + 1}"

    @staticmethod
    def extract_disciplines_names(root: ET.Element) -> List[str]:
        """Извлечение списка названий дисциплин"""
        disciplines = []

        try:
            # Ищем все элементы ПланыСтроки
            for elem in root.iter():
                if elem.tag.endswith('ПланыСтроки'):
                    # Получаем название дисциплины (Дисциплина)
                    discipline_name = elem.get('Дисциплина', '')

                    if discipline_name and discipline_name.strip():
                        disciplines.append(discipline_name.strip())

            # Удаляем дубликаты, сохраняя порядок
            seen = set()
            unique_disciplines = []
            for disc in disciplines:
                if disc not in seen:
                    seen.add(disc)
                    unique_disciplines.append(disc)

            return unique_disciplines

        except Exception as e:
            print(f"Ошибка при извлечении дисциплин: {e}")
            return []


class XmlParsingService:
    """Сервис для парсинга XML файлов и формирования ResponseModel"""

    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self._root = None

    def _parse_xml(self) -> Optional[ET.Element]:
        """Парсинг XML файла"""
        try:
            content = self.file_manager.read_file_content()
            if not content:
                return None

            # Пробуем разные кодировки
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

    def extract_response_data(self) -> ResponseModel:
        """Извлечение данных и формирование ResponseModel"""

        # Парсим XML
        root = self._parse_xml()
        if root is None:
            # Возвращаем пустую модель в случае ошибки
            current_year = datetime.now().year
            return ResponseModel(
                direction_code="",
                direction_name="",
                start_year=current_year,
                academic_year=f"{current_year}-{current_year + 1}",
                disciplines=[]
            )

        # Извлекаем данные
        direction_code = PlxDataExtractor.extract_direction_code(root)
        direction_name = PlxDataExtractor.extract_direction_name(root)
        start_year = PlxDataExtractor.extract_start_year(root)
        academic_year = PlxDataExtractor.extract_academic_year(root)
        disciplines = PlxDataExtractor.extract_disciplines_names(root)

        # Создаем и возвращаем модель ответа
        return ResponseModel(
            direction_code=direction_code,
            direction_name=direction_name,
            start_year=start_year,
            academic_year=academic_year,
            disciplines=disciplines
        )

    def print_response(self, response: ResponseModel) -> None:
        """Красивый вывод ResponseModel"""
        print("=" * 80)
        print("РЕЗУЛЬТАТ ПАРСИНГА PLX ФАЙЛА")
        print("=" * 80)
        print(f"\nКод направления: {response.direction_code}")
        print(f"Название направления: {response.direction_name}")
        print(f"Год начала обучения: {response.start_year}")
        print(f"Учебный год: {response.academic_year}")
        print(f"\nСписок дисциплин (всего: {len(response.disciplines)}):")
        print("-" * 80)

        if response.disciplines:
            for i, discipline in enumerate(response.disciplines, 1):
                print(f"{i:3}. {discipline}")
        else:
            print("  Дисциплины не найдены")

        print("=" * 80)


if __name__ == "__main__":
    path_to_file = "example.plx"

    if os.path.exists(path_to_file):
        print(f"Обработка файла: {path_to_file}\n")

        # Создаем FileManager
        file_manager = FileManager(path_to_file)

        # Создаем сервис парсинга
        parsing_service = XmlParsingService(file_manager)

        # Извлекаем данные в виде ResponseModel
        response = parsing_service.extract_response_data()

        # Выводим результат
        parsing_service.print_response(response)

    else:
        print(f"Файл {path_to_file} не найден.")