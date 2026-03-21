from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
import os
import xml.etree.ElementTree as ET
import re
from models.response_model_xml_parser import ResponseModel, DisciplineDetail


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
    def extract_disciplines_details(root: ET.Element) -> List[DisciplineDetail]:
        """Извлечение детальной информации о дисциплинах"""
        disciplines = []

        try:
            # Ищем все элементы ПланыСтроки
            for elem in root.iter():
                if elem.tag.endswith('ПланыСтроки'):
                    # Получаем название дисциплины
                    name = elem.get('Дисциплина', '')

                    # Пропускаем пустые названия
                    if not name or not name.strip():
                        continue

                    # Создаем объект с детальной информацией
                    discipline = DisciplineDetail(
                        name=name.strip(),
                        code=elem.get('ДисциплинаКод', '').strip() or None,
                        hours=elem.get('ЧасовПоПлану', '').strip() or None,
                        credits=elem.get('ТрудоемкостьКредитов', '').strip() or None,
                        department_code=elem.get('КодКафедры', '').strip() or None,
                        semester=elem.get('Семестр', '').strip() or None,
                        order=elem.get('Порядок', '').strip() or None,
                        block_code=elem.get('КодБлока', '').strip() or None,
                        object_type=elem.get('ТипОбъекта', '').strip() or None,
                        object_view=elem.get('ВидОбъекта', '').strip() or None,
                        actual_credits=elem.get('ЗЕТфакт', '').strip() or None,
                        studied_credits=elem.get('ЗЕТизучено', '').strip() or None,
                        actual_hours=elem.get('ЧасовПоЗЕТ', '').strip() or None,
                        studied_hours=elem.get('ЧасовИзучено', '').strip() or None,
                        hours_per_credit=elem.get('ЧасовВЗЕТ', '').strip() or None
                    )
                    disciplines.append(discipline)

            # Удаляем дубликаты по коду и названию
            seen = set()
            unique_disciplines = []
            for disc in disciplines:
                key = (disc.code, disc.name)
                if key not in seen:
                    seen.add(key)
                    unique_disciplines.append(disc)

            return unique_disciplines

        except Exception as e:
            print(f"Ошибка при извлечении детальной информации о дисциплинах: {e}")
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
        disciplines = PlxDataExtractor.extract_disciplines_details(root)

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
        print("=" * 120)
        print("РЕЗУЛЬТАТ ПАРСИНГА PLX ФАЙЛА")
        print("=" * 120)
        print(f"\nКод направления: {response.direction_code}")
        print(f"Название направления: {response.direction_name}")
        print(f"Год начала обучения: {response.start_year}")
        print(f"Учебный год: {response.academic_year}")
        print(f"\nДЕТАЛЬНЫЙ СПИСОК ДИСЦИПЛИН (всего: {len(response.disciplines)}):")
        print("=" * 120)

        if response.disciplines:
            for i, disc in enumerate(response.disciplines, 1):
                print(f"\n{i}. {disc.name}")
                print(f"   Код дисциплины: {disc.code or 'Не указан'}")
                print(f"   Часы: {disc.hours or 'Не указаны'}")
                print(f"   Кредиты: {disc.credits or 'Не указаны'}")
                print(f"   Код кафедры: {disc.department_code or 'Не указан'}")

                # Дополнительная информация
                details = []
                if disc.semester:
                    details.append(f"Семестр: {disc.semester}")
                if disc.order:
                    details.append(f"Порядок: {disc.order}")
                if disc.object_type:
                    details.append(f"Тип объекта: {disc.object_type}")
                if disc.object_view:
                    details.append(f"Вид объекта: {disc.object_view}")

                if details:
                    print(f"   Дополнительно: {', '.join(details)}")

                # Информация о ЗЕТ и часах
                credit_info = []
                if disc.actual_credits:
                    credit_info.append(f"Фактически ЗЕТ: {disc.actual_credits}")
                if disc.actual_hours:
                    credit_info.append(f"Фактически часов: {disc.actual_hours}")
                if disc.hours_per_credit:
                    credit_info.append(f"Часов в ЗЕТ: {disc.hours_per_credit}")

                if credit_info:
                    print(f"   Трудоемкость: {', '.join(credit_info)}")

                print("-" * 100)
        else:
            print("\n  Дисциплины не найдены")

        print("=" * 120)


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