from pathlib import Path
from typing import Dict, List, Any, Optional, Union, BinaryIO
from datetime import datetime
from dataclasses import dataclass
import os
import xml.etree.ElementTree as ET


@dataclass
class PlxParseResult:
    filename: str
    data: Dict[str, Any]
    errors: List[str]
    parse_time: datetime


class FileManager:
    def __init__(self, file_path: Union[Path, str]):
        self.file_path = Path(file_path) if isinstance(file_path, str) else file_path
        self._file_content = None
        self._file_object = None

    def read_first_line(self) -> str:

        try:
            with open(self.file_path, 'r', encoding='utf-16') as f:
                first_line = f.readline().strip()
                print(f"Первая строка файла: {first_line}")
                return first_line
        except Exception as e:
            print(f"Ошибка при чтении первой строки: {e}")
            return ""

    def read_all_lines(self) -> List[str]:

        lines = []
        try:
            with open(self.file_path, 'r', encoding='utf-16') as f:
                lines = [line.strip() for line in f.readlines()]
                print(f"Всего строк в файле: {len(lines)}")
            return lines
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return []

    def process_plx_file(self) -> List[List[str]]:

        first_line = self.read_first_line()

        try:
            tree = ET.parse(self.file_path)
            root = tree.getroot()

            elements_list = [[elem.tag] for elem in root.iter()]

            print(f"Список элементов (первые 5): {elements_list[:5]}")
            return elements_list

        except ET.ParseError as e:
            print(f"Ошибка парсинга XML: {e}")
            return []
        except Exception as e:
            print(f"Неожиданная ошибка: {e}")
            return []

    def read_file_content(self) -> bytes:

        try:
            with open(self.file_path, 'rb') as f:
                self._file_content = f.read()
            return self._file_content
        except Exception as e:
            print(f"Ошибка при чтении файла: {e}")
            return b""

    def get_file_info(self) -> Dict[str, Any]:

        info = {
            'filename': self.file_path.name,
            'path': str(self.file_path),
            'exists': self.file_path.exists()
        }

        if self.file_path.exists():
            info.update({
                'size_bytes': self.file_path.stat().st_size,
                'modified': datetime.fromtimestamp(self.file_path.stat().st_mtime)
            })

        return info


class XmlParsingService:
    def __init__(self, file_manager: FileManager):

        self.file_manager = file_manager
        self.results = []

    def parse_plx_files(self) -> List[PlxParseResult]:

        # Получаем содержимое файла через FileManager
        file_content = self.file_manager.read_file_content()

        # Получаем информацию о файле
        file_info = self.file_manager.get_file_info()
        filename = file_info['filename']

        # Парсим файл
        result = self._parse_single_plx(file_content, filename)
        self.results.append(result)

        return self.results

    def _parse_single_plx(self, content: bytes, filename: str) -> PlxParseResult:

        errors = []
        parsed_data = {
            'metadata': {},
            'items': [],
            'raw_structure': {}
        }

        try:
            root = ET.fromstring(content)

            parsed_data['metadata'] = {
                'filename': filename,
                'attributes': root.attrib,
                'root_tag': root.tag,
                'size_bytes': len(content)
            }

            parsed_data['raw_structure'] = self._parse_xml_element(root)

            items = self._extract_plx_items(root)
            if items:
                parsed_data['items'] = items

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

    def _extract_plx_items(self, root: ET.Element) -> List[Dict]:
        """Извлечение элементов из PLX структуры"""
        items = []

        for element in root.findall('.//item'):
            item_data = {
                'tag': element.tag,
                'attributes': element.attrib,
                'value': element.text.strip() if element.text else None,
            }

            children = {}
            for child in element:
                child_tag = child.tag
                child_value = child.text.strip() if child.text else None
                if child_tag in children:
                    if not isinstance(children[child_tag], list):
                        children[child_tag] = [children[child_tag]]
                    children[child_tag].append(child_value)
                else:
                    children[child_tag] = child_value

            if children:
                item_data['children'] = children

            items.append(item_data)

        return items

    def find_elements_by_tag(self, tag_name: str) -> List[Dict]:
        """Поиск элементов по имени тега"""
        found_elements = []

        for result in self.results:
            if not result.errors:
                elements = self._find_in_structure(result.data['raw_structure'], tag_name)
                for element in elements:
                    found_elements.append({
                        'filename': result.filename,
                        'element': element
                    })

        return found_elements

    def _find_in_structure(self, structure: Dict, tag_name: str) -> List[Dict]:
        """Рекурсивный поиск элементов по тегу"""
        found = []

        if structure.get('tag') == tag_name:
            found.append(structure)

        for child in structure.get('children', []):
            found.extend(self._find_in_structure(child, tag_name))

        return found

    def extract_attributes(self, tag_name: str, attr_name: str) -> List[Dict]:
        """Извлечение конкретных атрибутов"""
        attributes = []
        elements = self.find_elements_by_tag(tag_name)

        for element_info in elements:
            element = element_info['element']
            if attr_name in element.get('attributes', {}):
                attributes.append({
                    'filename': element_info['filename'],
                    'value': element['attributes'][attr_name]
                })

        return attributes

    def get_statistics(self) -> Dict:
        """Получение статистики по обработанным файлам"""
        stats = {
            'total_files': len(self.results),
            'successful_files': 0,
            'failed_files': 0,
            'total_items': 0,
            'unique_tags': set()
        }

        for result in self.results:
            if not result.errors:
                stats['successful_files'] += 1
                stats['total_items'] += len(result.data.get('items', []))

                self._collect_tags(result.data['raw_structure'], stats['unique_tags'])
            else:
                stats['failed_files'] += 1

        stats['unique_tags'] = list(stats['unique_tags'])
        return stats

    def _collect_tags(self, structure: Dict, tags_set: set):
        """Рекурсивный сбор уникальных тегов"""
        if structure.get('tag'):
            tags_set.add(structure.get('tag'))
        for child in structure.get('children', []):
            self._collect_tags(child, tags_set)


if __name__ == "__main__":

    # Создаем экземпляр FileManager с путем к файлу
    path_to_file = "example.plx"

    # Проверяем существование файла
    if os.path.exists(path_to_file):
        # Создаем FileManager
        file_manager = FileManager(path_to_file)

        # Получаем информацию о файле
        file_info = file_manager.get_file_info()
        print(f"\nИнформация о файле:")
        for key, value in file_info.items():
            print(f"  {key}: {value}")

        # Обрабатываем файл: читаем первую строку и создаем список элементов
        print(f"\nОбработка файла {path_to_file}:")
        elements_list = file_manager.process_plx_file()

        # Выводим результат
        print(f"\nРезультат обработки:")
        print(f"Всего элементов: {len(elements_list)}")

        # Показываем первые 10 элементов для примера
        print(f"\nПервые 10 элементов (список списков с тегами):")
        for i, element in enumerate(elements_list[:10], 1):
            print(f"  Элемент {i}: {element}")

        # Дополнительно: читаем все строки файла
        print(f"\nЧтение всех строк файла:")
        all_lines = file_manager.read_all_lines()
        print(f"Первые 5 строк из {len(all_lines)}:")
        for i, line in enumerate(all_lines[:5], 1):
            print(f"  Строка {i}: {line}")

        # Используем XmlParsingService для более глубокого парсинга
        print(f"\n" + "=" * 60)
        print("Детальный парсинг через XmlParsingService")
        print("=" * 60)

        parsing_service = XmlParsingService(file_manager)
        results = parsing_service.parse_plx_files()

        for result in results:
            if result.errors:
                print(f"Ошибки в {result.filename}: {result.errors}")
            else:
                print(f"\nУспешно обработан {result.filename}")
                print(f"Метаданные: {result.data['metadata']}")
                print(f"Найдено элементов 'item': {len(result.data['items'])}")

        # Статистика
        stats = parsing_service.get_statistics()
        print(f"\nСтатистика: {stats}")

        # Поиск элементов по тегу
        found_items = parsing_service.find_elements_by_tag('item')
        print(f"Найдено элементов с тегом 'item': {len(found_items)}")

    else:
        print(f"Файл {path_to_file} не найден.")