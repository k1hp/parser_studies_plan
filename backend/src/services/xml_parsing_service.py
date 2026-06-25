from datetime import datetime
import os
import io
import zipfile
import xml.etree.ElementTree as ET
import re
from pathlib import Path

from src.utils import applogger
from src.schemas.xml_schemas import ResponseModel, DisciplineDetail, PracticeDetail
from src.services.file_manager import FileManager


class PlxDataExtractor:

    @staticmethod
    def extract_direction_code(root: ET.Element) -> str:
        """ Извлекает код направления подготовки из XML, учитывая различные структуры представления данных и обеспечивая устойчивость к отсутствию данных."""
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
        """ Извлекает название направления подготовки и профиль из XML-элемента ООП, учитывая различные структуры представления данных."""
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
        """Извлекает год начала обучения из XML, пытаясь найти его в атрибутах и обрабатывая различные форматы представления года."""
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
        """Извлекает список дисциплин из XML, разделяя и тем самым обеспечивая уникальность по названию и коду."""
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

    @staticmethod
    def extract_items(root: ET.Element) -> tuple[list[DisciplineDetail], list[PracticeDetail]]:
        disciplines = []
        practices = []
        seen_disciplines = set()
        seen_practices = set()

        for elem in root.iter():
            if elem.tag.endswith('ПланыСтроки'):
                name = elem.get('Дисциплина', '').strip()
                code = elem.get('ДисциплинаКод', '').strip() or None
                obj_type = elem.get('ТипОбъекта', '')

                if not name:
                    continue

                if obj_type == '2':  # дисциплина
                    key = (name, code)
                    if key not in seen_disciplines:
                        seen_disciplines.add(key)
                        disciplines.append(
                            DisciplineDetail(discipline_name=name, discipline_code=code)
                        )
                elif obj_type == '3':  # практика
                    key = (name, code)
                    if key not in seen_practices:
                        seen_practices.add(key)
                        practices.append(
                            PracticeDetail(discipline_name=name, discipline_code=code)
                        )

        return disciplines, practices

class XmlParsingService:
    """Класс, отвечающий за парсинг XML-структур."""

    def __init__(self):
        self._root = None

    def _parse_xml(self, content: bytes) -> ET.Element | None:
        """Пытается распарсить XML из байтового контента, используя несколько кодировок.
        Если контент — ZIP-архив (PLX), сначала извлекает XML из архива."""
        if not content:
            return None

        # PLX-файлы — это ZIP-архивы с XML внутри
        if content[:2] == b'PK':
            content = self._extract_xml_from_zip(content)
            if content is None:
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

    def _extract_xml_from_zip(self, content: bytes) -> bytes | None:
        """Извлекает XML из ZIP-архива (PLX-файла)."""
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                xml_files = [n for n in zf.namelist() if n.lower().endswith('.xml')]
                if not xml_files:
                    applogger.warning("PLX-архив не содержит XML-файлов")
                    return None
                # берём первый XML (обычно он один) или тот что без __MACOSX
                target = xml_files[0]
                for name in xml_files:
                    if '__MACOSX' not in name:
                        target = name
                        break
                applogger.info(f"Извлечён XML из PLX: {target}")
                return zf.read(target)
        except zipfile.BadZipFile as e:
            applogger.error(f"PLX-файл повреждён или не является ZIP: {e}")
            return None
        except Exception as e:
            applogger.error(f"Ошибка чтения PLX-архива: {e}")
            return None

    def extract_all(self, contents: list[bytes]) -> list[ResponseModel | PracticeDetail]:
        results = []
        for content in contents:
            response = self.extract_from_content(content)
            if response:
                results.append(response)
        return results

    def extract_from_content(self, content: bytes) -> ResponseModel | None:
        """Извлекает данные из одного XML-файла, возвращая модель ResponseModel или None в случае ошибок."""
        root = self._parse_xml(content)

        if root is None:
            applogger.warning("Не удалось извлечь root из контента (XML/PLX пустой).")
            return None

        direction_code = PlxDataExtractor.extract_direction_code(root)
        direction_name, profile_name = PlxDataExtractor.extract_direction_name(root)
        start_year = PlxDataExtractor.extract_start_year(root)
        disciplines, practices = PlxDataExtractor.extract_items(root)

        full_direction_name = f"{direction_name}, {profile_name}" if profile_name else direction_name

        return ResponseModel(
            direction_code=direction_code,
            direction_name=full_direction_name,
            start_year=start_year,
            disciplines=disciplines,
            practices=practices
        )



if __name__ == "__main__":
    current_script_dir = os.path.dirname(os.path.abspath(__file__))
    folder_path = str(Path.home() / "Downloads")
    file_manager = FileManager(folder_path)
    extractor = XmlParsingService()
    files = file_manager.get_files_in_directory()
    contents = file_manager.get_files_contents(files)

    if files:
        for file_path, content in zip(files, contents):
            response = extractor.extract_from_content(content)
            if response:
                applogger.info(response.model_dump_json(indent=2, ensure_ascii=False))
    else:
        applogger.info(f"Файлы не найдены в директории: {folder_path}")