from pathlib import Path
from typing import Dict, List, Any, Optional, Union, BinaryIO
from datetime import datetime
from dataclasses import dataclass, asdict
import os
import xml.etree.ElementTree as ET
import re


@dataclass
class PlxParseResult:
    filename: str
    data: Dict[str, Any]
    errors: List[str]
    parse_time: datetime


@dataclass
class GroupInfo:
    """Информация о группе"""
    group_name: str  # XXXX-XXX-99
    code: str  # шифр направления
    name: str  # название направления
    profile: str  # профиль
    academic_year: str  # учебный год


@dataclass
class DocumentInfo:
    """Информация о документе из атрибутов корневого элемента"""
    type: str
    prev_name: str
    last_name: str
    prev_write: str
    last_write: str
    user_name: str
    user_pc: str
    courses_count: str
    semesters_per_course: str


@dataclass
class OOPInfo:
    """Информация об ООП (Основная образовательная программа)"""
    code: str
    шифр: str
    название: str
    level: str
    qualification: str
    duration_years: str
    document_number: str
    document_date: str
    type_gos: str


@dataclass
class DirectionInfo:
    """Информация о направлении"""
    шифр: str
    название: str
    profile: str


@dataclass
class DisciplineInfo:
    """Информация о дисциплине"""
    code: str  # код дисциплины (ДисциплинаКод)
    name: str  # название дисциплины (Дисциплина)
    department_code: Optional[str] = None  # КодКафедры
    credits: Optional[str] = None  # ТрудоемкостьКредитов
    hours: Optional[str] = None  # ЧасовПоПлану
    hours_per_credit: Optional[str] = None  # ЧасовВЗЕТ
    фактически_зет: Optional[str] = None  # ЗЕТфакт
    изучено_зет: Optional[str] = None  # ЗЕТизучено
    фактически_часов: Optional[str] = None  # ЧасовПоЗЕТ
    изучено_часов: Optional[str] = None  # ЧасовИзучено
    номер: Optional[str] = None  # Номер
    порядок: Optional[str] = None  # Порядок
    тип_объекта: Optional[str] = None  # ТипОбъекта
    вид_объекта: Optional[str] = None  # ВидОбъекта
    уровень_вложения: Optional[str] = None  # УровеньВложения
    код_блока: Optional[str] = None  # КодБлока


@dataclass
class CurriculumData:
    """Структурированные данные учебного плана"""
    document_info: DocumentInfo
    oop_info: OOPInfo
    direction_info: DirectionInfo
    disciplines: List[DisciplineInfo]
    total_disciplines: int
    file_info: Dict[str, Any]
    raw_attributes: Dict[str, Any]


class FileManager:
    def __init__(self, file_path: Union[Path, str]):
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path
        self._file_content = None
        self._file_object = None

    def read_file_content(self) -> bytes:
        """Чтение всего содержимого файла в байтах"""
        try:
            with open(self.file_path, 'rb') as f:
                self._file_content = f.read()
            return self._file_content
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return b""

    def get_file_info(self) -> Dict[str, Any]:
        """Получение информации о файле"""
        info = {
            'filename': self.file_path.name,
            'path': str(self.file_path),
            'exists': self.file_path.exists()
        }

        if self.file_path.exists():
            info.update({
                'size_bytes': self.file_path.stat().st_size,
                'modified': datetime.fromtimestamp(self.file_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            })

        return info


class PlxDataExtractor:
    """Класс для извлечения специфических данных из PLX файлов"""

    @staticmethod
    def extract_document_info(root: ET.Element) -> DocumentInfo:
        """Извлечение информации из атрибутов корневого элемента Документ"""
        attrib = root.attrib

        return DocumentInfo(
            type=attrib.get('Тип', ''),
            prev_name=attrib.get('PrevName', ''),
            last_name=attrib.get('LastName', ''),
            prev_write=attrib.get('PrevWrite', ''),
            last_write=attrib.get('LastWrite', ''),
            user_name=attrib.get('UserName', ''),
            user_pc=attrib.get('UserPC', ''),
            courses_count=attrib.get('ЧислоКурсов', ''),
            semesters_per_course=attrib.get('СеместровНаКурсе', '')
        )

    @staticmethod
    def extract_oop_info(root: ET.Element) -> OOPInfo:
        """Извлечение информации об ООП (Основная образовательная программа)"""
        oop_info = OOPInfo(
            code="",
            шифр="",
            название="",
            level="",
            qualification="",
            duration_years="",
            document_number="",
            document_date="",
            type_gos=""
        )

        try:
            # Ищем все элементы ООП
            for elem in root.iter():
                if elem.tag.endswith('ООП'):
                    oop_info.code = elem.get('Код', '')
                    oop_info.шифр = elem.get('Шифр', '')
                    oop_info.название = elem.get('Название', '')
                    oop_info.level = elem.get('УровеньОбразования', '')
                    oop_info.qualification = elem.get('Квалификация', '')
                    oop_info.duration_years = elem.get('СрокЛет', '')
                    oop_info.document_number = elem.get('НомерДокумента', '')
                    oop_info.document_date = elem.get('ДатаДокумента', '')
                    oop_info.type_gos = elem.get('ТипГОСа', '')

                    # Если нашли основной элемент ООП, выходим
                    if oop_info.шифр or oop_info.название:
                        break

        except Exception as e:
            print(f"Ошибка при извлечении информации об ООП: {e}")

        return oop_info

    @staticmethod
    def extract_direction_info(root: ET.Element) -> DirectionInfo:
        """Извлечение информации о направлении"""
        direction_info = DirectionInfo(
            шифр="",
            название="",
            profile=""
        )

        try:
            # Поиск вложенного ООП (профиль)
            for elem in root.iter():
                if elem.tag.endswith('ООП'):
                    # Проверяем, является ли элемент вложенным (профилем)
                    parent = PlxDataExtractor._find_parent(root, elem)
                    if parent is not None and parent.tag.endswith('ООП'):
                        direction_info.profile = elem.get('Название', '')

                    # Основной шифр и название
                    if not direction_info.шифр:
                        direction_info.шифр = elem.get('Шифр', '')
                    if not direction_info.название:
                        direction_info.название = elem.get('Название', '')

        except Exception as e:
            print(f"Ошибка при извлечении информации о направлении: {e}")

        return direction_info

    @staticmethod
    def _find_parent(root: ET.Element, child: ET.Element) -> Optional[ET.Element]:
        """Поиск родительского элемента"""
        for elem in root.iter():
            for subelem in elem:
                if subelem is child:
                    return elem
        return None

    @staticmethod
    def extract_disciplines(root: ET.Element) -> List[DisciplineInfo]:
        """Извлечение информации о дисциплинах из элемента ПланыСтроки"""
        disciplines = []

        try:
            # Ищем все элементы ПланыСтроки
            for elem in root.iter():
                if elem.tag.endswith('ПланыСтроки'):
                    # Получаем код дисциплины (ДисциплинаКод)
                    code = elem.get('ДисциплинаКод', '')

                    # Получаем название дисциплины (Дисциплина)
                    name = elem.get('Дисциплина', '')

                    if code or name:  # Добавляем только если есть хотя бы код или название
                        discipline = DisciplineInfo(
                            code=code.strip(),
                            name=name.strip(),
                            department_code=elem.get('КодКафедры', '').strip() or None,
                            credits=elem.get('ТрудоемкостьКредитов', '').strip() or None,
                            hours=elem.get('ЧасовПоПлану', '').strip() or None,
                            hours_per_credit=elem.get('ЧасовВЗЕТ', '').strip() or None,
                            фактически_зет=elem.get('ЗЕТфакт', '').strip() or None,
                            изучено_зет=elem.get('ЗЕТизучено', '').strip() or None,
                            фактически_часов=elem.get('ЧасовПоЗЕТ', '').strip() or None,
                            изучено_часов=elem.get('ЧасовИзучено', '').strip() or None,
                            номер=elem.get('Номер', '').strip() or None,
                            порядок=elem.get('Порядок', '').strip() or None,
                            тип_объекта=elem.get('ТипОбъекта', '').strip() or None,
                            вид_объекта=elem.get('ВидОбъекта', '').strip() or None,
                            уровень_вложения=elem.get('УровеньВложения', '').strip() or None,
                            код_блока=elem.get('КодБлока', '').strip() or None
                        )
                        disciplines.append(discipline)

            # Удаляем дубликаты (по коду и названию)
            seen = set()
            unique_disciplines = []
            for disc in disciplines:
                key = (disc.code, disc.name)
                if key not in seen:
                    seen.add(key)
                    unique_disciplines.append(disc)

            disciplines = unique_disciplines

        except Exception as e:
            print(f"Ошибка при извлечении дисциплин: {e}")

        return disciplines

    @staticmethod
    def extract_all_attributes(root: ET.Element) -> Dict[str, Any]:
        """Извлечение всех атрибутов из всего XML"""
        all_attributes = {}

        try:
            # Атрибуты корневого элемента
            all_attributes['Документ'] = dict(root.attrib)

            # Атрибуты всех элементов
            for elem in root.iter():
                if elem.attrib:
                    tag = elem.tag.split('}')[-1] if '}' in elem.tag else elem.tag
                    if tag not in all_attributes:
                        all_attributes[tag] = []
                    all_attributes[tag].append(dict(elem.attrib))

        except Exception as e:
            print(f"Ошибка при извлечении атрибутов: {e}")

        return all_attributes

    @staticmethod
    def format_output(curriculum_data: CurriculumData) -> str:
        """Форматирование вывода данных в стиле Шифр=..., Название=..."""
        output_lines = []

        # Заголовок
        output_lines.append("=" * 120)
        output_lines.append(f"ДАННЫЕ ИЗ УЧЕБНОГО ПЛАНА")
        output_lines.append("=" * 120)

        # Информация о файле
        output_lines.append("\nИНФОРМАЦИЯ О ФАЙЛЕ:")
        output_lines.append(f"  Файл={curriculum_data.file_info.get('filename', 'N/A')}")
        output_lines.append(f"  Размер={curriculum_data.file_info.get('size_bytes', 0)} байт")
        output_lines.append(f"  Изменен={curriculum_data.file_info.get('modified', 'N/A')}")

        # Информация из корневого элемента Документ
        output_lines.append("\nИНФОРМАЦИЯ О ДОКУМЕНТЕ:")
        output_lines.append(f"  Тип={curriculum_data.document_info.type}")
        output_lines.append(f"  Предыдущее имя={curriculum_data.document_info.prev_name}")
        output_lines.append(f"  Последнее имя={curriculum_data.document_info.last_name}")
        output_lines.append(f"  Предыдущее изменение={curriculum_data.document_info.prev_write}")
        output_lines.append(f"  Последнее изменение={curriculum_data.document_info.last_write}")
        output_lines.append(f"  Пользователь={curriculum_data.document_info.user_name}")
        output_lines.append(f"  Компьютер={curriculum_data.document_info.user_pc}")
        output_lines.append(f"  Число курсов={curriculum_data.document_info.courses_count}")
        output_lines.append(f"  Семестров на курсе={curriculum_data.document_info.semesters_per_course}")

        # Информация об ООП
        output_lines.append("\nИНФОРМАЦИЯ ОБ ООП (Основная образовательная программа):")
        output_lines.append(f"  Код={curriculum_data.oop_info.code}")
        output_lines.append(f"  Шифр={curriculum_data.oop_info.шифр}")
        output_lines.append(f"  Название={curriculum_data.oop_info.название}")
        output_lines.append(f"  Уровень образования={curriculum_data.oop_info.level}")
        output_lines.append(f"  Квалификация={curriculum_data.oop_info.qualification}")
        output_lines.append(f"  Срок (лет)={curriculum_data.oop_info.duration_years}")
        output_lines.append(f"  Номер документа={curriculum_data.oop_info.document_number}")
        output_lines.append(f"  Дата документа={curriculum_data.oop_info.document_date}")
        output_lines.append(f"  Тип ГОСа={curriculum_data.oop_info.type_gos}")

        # Информация о направлении и профиле
        output_lines.append("\nИНФОРМАЦИЯ О НАПРАВЛЕНИИ И ПРОФИЛЕ:")
        output_lines.append(f"  Шифр направления={curriculum_data.direction_info.шифр}")
        output_lines.append(f"  Название направления={curriculum_data.direction_info.название}")
        output_lines.append(f"  Профиль={curriculum_data.direction_info.profile}")

        # Информация о дисциплинах
        output_lines.append(f"\nДИСЦИПЛИНЫ (всего: {curriculum_data.total_disciplines}):")
        output_lines.append("-" * 120)

        if curriculum_data.disciplines:
            # Заголовок таблицы
            output_lines.append(
                f"{'№':<4} {'Код дисциплины':<15} {'Название дисциплины':<40} {'Кафедра':<8} {'Кредиты':<8} {'Часы':<8} {'ЗЕТфакт':<8} {'Номер':<6}"
            )
            output_lines.append("-" * 120)

            # Строки с дисциплинами
            for i, disc in enumerate(curriculum_data.disciplines, 1):
                code = disc.code[:13] + ".." if len(disc.code) > 13 else disc.code
                name = disc.name[:38] + ".." if len(disc.name) > 38 else disc.name
                department = disc.department_code or '-'
                credits = disc.credits or '-'
                hours = disc.hours or '-'
                фактически_зет = disc.фактически_зет or '-'
                номер = disc.номер or '-'

                output_lines.append(
                    f"{i:<4} {code:<15} {name:<40} {department:<8} {credits:<8} {hours:<8} {фактически_зет:<8} {номер:<6}"
                )

            # Детальная информация о дисциплинах
            output_lines.append("\nДЕТАЛЬНАЯ ИНФОРМАЦИЯ О ДИСЦИПЛИНАХ:")
            output_lines.append("-" * 120)

            for i, disc in enumerate(curriculum_data.disciplines, 1):
                output_lines.append(f"\n{i}. {disc.name} (Код: {disc.code}):")
                output_lines.append(f"   Кафедра: {disc.department_code or 'Не указана'}")
                output_lines.append(f"   Трудоемкость: {disc.credits or '0'} кредитов, {disc.hours or '0'} часов")
                output_lines.append(f"   Часов в ЗЕТ: {disc.hours_per_credit or '36'}")
                output_lines.append(
                    f"   Фактически ЗЕТ: {disc.фактически_зет or '0'}, Изучено ЗЕТ: {disc.изучено_зет or '0'}")
                output_lines.append(
                    f"   Фактически часов: {disc.фактически_часов or '0'}, Изучено часов: {disc.изучено_часов or '0'}")
                output_lines.append(f"   Номер: {disc.номер or '-'}, Порядок: {disc.порядок or '-'}")
                output_lines.append(
                    f"   Тип объекта: {disc.тип_объекта or '-'}, Вид объекта: {disc.вид_объекта or '-'}")
                output_lines.append(
                    f"   Уровень вложения: {disc.уровень_вложения or '-'}, Код блока: {disc.код_блока or '-'}")
        else:
            output_lines.append("  Дисциплины не найдены")

        # Вывод сырых атрибутов (для отладки)
        output_lines.append("\n" + "=" * 120)
        output_lines.append("СЫРЫЕ АТРИБУТЫ ИЗ ФАЙЛА (первые 5 элементов ПланыСтроки):")
        output_lines.append("=" * 120)

        for tag, attrs_list in curriculum_data.raw_attributes.items():
            if tag == 'Документ':
                output_lines.append(f"\n{tag}:")
                for key, value in attrs_list.items():
                    output_lines.append(f"  {key}={value}")
            elif tag == 'ПланыСтроки' and attrs_list:
                output_lines.append(f"\n{tag} (первые 5):")
                for i, attrs in enumerate(attrs_list[:5]):
                    output_lines.append(f"\n  Элемент {i + 1}:")
                    # Выводим только ключевые атрибуты для наглядности
                    for key in ['Дисциплина', 'ДисциплинаКод', 'КодКафедры', 'ТрудоемкостьКредитов', 'ЧасовПоПлану']:
                        if key in attrs:
                            output_lines.append(f"    {key}={attrs[key]}")

        return "\n".join(output_lines)


class XmlParsingService:
    def __init__(self, file_manager: FileManager):
        self.file_manager = file_manager
        self.results = []

    def parse_plx_files(self) -> List[PlxParseResult]:
        """Парсинг PLX файла через FileManager"""
        file_content = self.file_manager.read_file_content()
        file_info = self.file_manager.get_file_info()
        filename = file_info['filename']

        result = self._parse_single_plx(file_content, filename)
        self.results.append(result)

        return self.results

    def _parse_single_plx(self, content: bytes, filename: str) -> PlxParseResult:
        """Парсинг одного PLX файла"""
        errors = []
        parsed_data = {
            'metadata': {},
            'items': [],
            'raw_structure': {}
        }

        try:
            # Пробуем разные кодировки
            try:
                # Сначала пробуем utf-8
                xml_str = content.decode('utf-8')
            except UnicodeDecodeError:
                # Если не получилось, пробуем utf-16 (как в примере)
                xml_str = content.decode('utf-16')

            root = ET.fromstring(xml_str)

            parsed_data['metadata'] = {
                'filename': filename,
                'attributes': root.attrib,
                'root_tag': root.tag,
                'size_bytes': len(content)
            }

            parsed_data['raw_structure'] = self._parse_xml_element(root)

        except ET.ParseError as e:
            errors.append(f"Ошибка парсинга XML: {str(e)}")
        except Exception as e:
            errors.append(f"Неожиданная ошибка: {str(e)}")

        return PlxParseResult(
            filename=filename,
            data=parsed_data,
            errors=errors,
            parse_time=datetime.now()
        )

    def _parse_xml_element(self, element: ET.Element) -> Dict:
        """Рекурсивный парсинг XML элемента"""
        result = {
            'tag': element.tag,
            'attributes': element.attrib,
            'text': element.text.strip() if element.text and element.text.strip() else None,
            'children': []
        }

        for child in element:
            result['children'].append(self._parse_xml_element(child))

        return result

    def extract_curriculum_data(self) -> CurriculumData:
        """Извлечение структурированных данных учебного плана"""
        if not self.results:
            self.parse_plx_files()

        result = self.results[0] if self.results else None

        if not result or result.errors:
            return CurriculumData(
                document_info=DocumentInfo("", "", "", "", "", "", "", "", ""),
                oop_info=OOPInfo("", "", "", "", "", "", "", "", ""),
                direction_info=DirectionInfo("", "", ""),
                disciplines=[],
                total_disciplines=0,
                file_info=self.file_manager.get_file_info(),
                raw_attributes={}
            )

        try:
            content = self.file_manager.read_file_content()

            # Пробуем разные кодировки
            try:
                xml_str = content.decode('utf-8')
            except UnicodeDecodeError:
                xml_str = content.decode('utf-16')

            root = ET.fromstring(xml_str)

            # Извлечение всей информации
            document_info = PlxDataExtractor.extract_document_info(root)
            oop_info = PlxDataExtractor.extract_oop_info(root)
            direction_info = PlxDataExtractor.extract_direction_info(root)
            disciplines = PlxDataExtractor.extract_disciplines(root)
            raw_attributes = PlxDataExtractor.extract_all_attributes(root)

            print(f"Найдено дисциплин: {len(disciplines)}")  # Отладочный вывод

            return CurriculumData(
                document_info=document_info,
                oop_info=oop_info,
                direction_info=direction_info,
                disciplines=disciplines,
                total_disciplines=len(disciplines),
                file_info=self.file_manager.get_file_info(),
                raw_attributes=raw_attributes
            )

        except Exception as e:
            print(f"Ошибка при извлечении данных: {e}")
            import traceback
            traceback.print_exc()
            return CurriculumData(
                document_info=DocumentInfo("", "", "", "", "", "", "", "", ""),
                oop_info=OOPInfo("", "", "", "", "", "", "", "", ""),
                direction_info=DirectionInfo("", "", ""),
                disciplines=[],
                total_disciplines=0,
                file_info=self.file_manager.get_file_info(),
                raw_attributes={}
            )


if __name__ == "__main__":
    path_to_file = "example.plx"

    if os.path.exists(path_to_file):
        print(f"Обработка файла: {path_to_file}")
        print("=" * 120)

        # Создаем FileManager
        file_manager = FileManager(path_to_file)

        # Создаем сервис парсинга
        parsing_service = XmlParsingService(file_manager)

        # Извлекаем структурированные данные
        curriculum_data = parsing_service.extract_curriculum_data()

        # Форматируем и выводим результат
        output = PlxDataExtractor.format_output(curriculum_data)
        print(output)

    else:
        print(f"Файл {path_to_file} не найден.")