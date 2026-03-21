import json
from typing import List
import requests
from bs4 import BeautifulSoup
import logging
from pydantic import BaseModel, Field, HttpUrl, ValidationError
from datetime import datetime
from typing import Dict, Any, List, Optional
import pprint

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class CurriculumModel(BaseModel):
    # verification_date: str = Field(default_factory=lambda: datetime.now().strftime('%d.%m.%Y %H:%M:%S'))
    # curriculum_file: str
    # site_url: HttpUrl
    specialty: str
    curriculum_year: str
    lvl_education: str
    form_education: str
    education_program: bool
    calendar_graphic: bool
    curriculum_plan: bool
    gia_program: bool
    education_program_vosp: bool
    education_plan_vosp: bool
    all_programs: List[str] = []  # все элементы из страницы 
    working_programs: List[str] = []  
    fos_materials: List[str] = []  
    practic_programs: List[str] = []  
    methodical_materials: List[str] = []  

    @classmethod
    def validate_dict(cls, payload: Dict[str, Any]) -> "CurriculumModel":
        return cls.model_validate(payload)


class WebParsingService:
    selectors: Dict[str, str] = {
        "specialty": "h1",
    }

    def __init__(self, url: str, curriculum_file: str = "plan.xml"):
        self.url = url
        self.curriculum_file = curriculum_file
    
    # output text based on selectors
    def _get_text(self, soup: BeautifulSoup, selector: str) -> Optional[str]:
        el = soup.select_one(selector)
        return el.get_text(strip=True) if el else None

    # for level iducation etc
    def _get_text_after_label(self, soup: BeautifulSoup, label: str) -> str:
        elem = soup.find(string=lambda x: x and label in x)
        if elem:
            next_elem = elem.find_next_sibling()
            if next_elem:
                return next_elem.get_text(strip=True)
        return ""
    
    # years of admitiont
    def _get_year_from_title(self, soup: BeautifulSoup) -> str:
        h1 = soup.find('h1')
        if h1:
            import re
            match = re.search(r'приём\s+([\d,\s]+)', h1.get_text(), re.IGNORECASE) # ё не существует
            if match:
                return match.group(1).strip()
        return ""
    
    #checks has a page part with given name
    def _section_exists(self, soup: BeautifulSoup, section_name: str) -> bool:
        
        return bool(soup.find(string=lambda x: x and section_name in x))

    # the text is similar to a section heading.
    def _is_section_header(self, text: str) -> bool:
        
        headers = [
            "Образовательная программа", "Уровень образования", "Форма обучения",
            "Календарный учебный график", "Учебный план", "Рабочие программы дисциплин",
            "ФОС", "Методические материалы", "Рабочая программа воспитания",
            "Календарный план воспитательной работы", "Практики"
        ]
        return text in headers
    
    # deepseak, sry(
    def _get_section_items(self, soup: BeautifulSoup, section_name: str) -> List[str]:
        """Собирает все дисциплины из раздела (строки с 2+ точками)"""
        items = []

        header = soup.find(string=lambda x: x and section_name in x)
        if not header:
            return items
        
        current = header.find_next()
        while current:
            text = current.get_text(strip=True)
            
            if text and len(text) < 50 and any(c.isalpha() for c in text):
                if self._is_section_header(text):
                    break
            
            # отбор по точкам
            if text and text.count('.') >= 2:
                # проверка на отсутсвие пробелом
                if text.count('.') > 4 and ' ' in text:
                    # добавляем пробел
                    parts = text.split()
                    for part in parts:
                        if part.count('.') >= 2:
                            items.append(part)
                else:
                    items.append(text)
            
            current = current.find_next()
        
        return items

    def parse(self) -> Dict[str, Any]:
        logger.info("Start parsing URL %s", self.url)
        response = requests.get(self.url)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        logger.info("Page loaded, length=%s", len(response.text))


        all_data = [
            el.get_text(strip=True)
            for el in soup.select("h1, p, li")
            if el.get_text(strip=True)
        ]

        data: Dict[str, Any] = {
            # "verification_date": datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
            # "curriculum_file": self.curriculum_file,
            # "site_url": self.url,
            "specialty": self._get_text(soup, self.selectors["specialty"]) or "",
            "curriculum_year": self._get_year_from_title(soup),
            "lvl_education": self._get_text_after_label(soup, "Уровень образования"),
            "form_education": self._get_text_after_label(soup, "Форма обучения"),
            "education_program": self._section_exists(soup, "Рабочие программы дисциплин"),
            "calendar_graphic": self._section_exists(soup, "Календарный учебный график"),
            "curriculum_plan": self._section_exists(soup, "Учебный план"),
            "gia_program": self._section_exists(soup, "ГИА"),
            "education_program_vosp": self._section_exists(soup, "Рабочая программа воспитания"),
            "education_plan_vosp": self._section_exists(soup, "Календарный план воспитательной работы"),
            "all_programs": all_data,
            "working_programs": self._get_section_items(soup, "Рабочие программы дисциплин"),
            "fos_materials": self._get_section_items(soup, "ФОС"),
            "practic_programs": self._get_section_items(soup, "Практики"),
            "methodical_materials": self._get_section_items(soup, "Методические материалы"),
        }

        logger.info("Parsed %d items, found %d working programs", 
                   len(all_data), len(data["working_programs"]))
        return data
    #validation based on pydantic2
    def parse_and_validate(self) -> CurriculumModel:
        data = self.parse()
        return CurriculumModel.validate_dict(data)
        

if __name__ == "__main__":
    service = WebParsingService("https://mauniver.ru/sveden/education/op/43292#prak")
    result = service.parse_and_validate()
    pprint.pprint(result.model_dump_json())
