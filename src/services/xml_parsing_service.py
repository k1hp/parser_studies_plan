from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass
import os
from xml import etree

@dataclass
class PlxParseResult:
    filename: str
    data: Dict[str, Any]
    errors: List[str]
    parse_time: datetime

class XmlParsingService:
    def __init__(self, files: dict | bytes):
        self.files = files
        self.results = []

    def parse_plx_files(self) -> list[PlxParseResult]:
        if isinstance(self.files, dict):
            for filename, content in self.files.items():
                result = self._parse_single_plx(content, filename)
                self.results.append(result)
        else:
            result = self._parse_single_plx(self.files)
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

            root = etree.fromstring(content)

            parsed_data['metadata'] = {
                'filename': filename,
                'attribute': root.attrib,
                'root_tag': root.tag,
                'size_bytes': len(content)
            }

            parsed_data['raw_structure'] = self._parse_xml_element(root)

            items = self._extract_plx_items(root)
            if items:
                parsed_data['items'] = items
        except etree.ParseError as e:
            errors.append(f"Ошибка парсинга XML: {str(e)}")
        except Exception as e:
            errors.append(f"Неожиданная ошибка: {str(e)}")

        return PlxParseResult(
            filename=filename,
            data=parsed_data,
            errors=errors,
            parse_time=datetime.now()
        )

    def _parse_xml_element(self, element: etree.Element) -> Dict:
        result = {
            'tag': element.tag,
            'attribute': element.attrib,
            'text': element.text.strip() if element.text and element.text.strip() else None,
            'children': []
        }

        for child in element:
            result['children'].append(self._parse_xml_element(child))
        return result

    def _extract_plx_items(self, root: etree.Element) -> List[Dict]:
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

        found = []

        if structure.get('tag') == tag_name:
            found.append(structure)

        for child in structure.get('children', []):
            found.extend(self._find_in_structure(child, tag_name))

        return found

    def extract_attributes(self, tag_name: str, attr_name: str) -> List[Dict]:

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
        tags_set.add(structure.get('tag'))
        for child in structure.get('children', []):
            self._collect_tags(child, tags_set)