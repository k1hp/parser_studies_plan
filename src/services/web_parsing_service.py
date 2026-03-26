from typing import List
import re
import requests
from bs4 import BeautifulSoup
import logging
from pydantic import BaseModel, Field, HttpUrl, ValidationError
from typing import Dict, Any, List, Optional
import pprint

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

class DisciplineDetail(BaseModel):
    discipline_name: str = Field(..., description="Название дисциплины")
    discipline_code: str = Field(..., description="Код дисциплины (ДисциплинаКод)")

class CurriculumModel(BaseModel):
    specialty: str = Field(..., description="Название специальности")
    discipline_code: str = Field(..., description="Код дисциплины")
    curriculum_year: str = Field(..., description="Год набора")
    education_program: bool = Field(..., description="Наличие раздела 'Образовательная программа'")
    lvl_education: str = Field(..., description="Уровень образования")
    form_education: str = Field(..., description="Форма обучения")
    calendar_graphic: bool = Field(..., description="Наличие календарного учебного графика")
    education_plan: bool = Field(..., description="Наличие учебного плана")
    
    working_programs: list[DisciplineDetail] = Field(default=[], description="Список рабочих программ дисциплин")
    fos_materials: list[DisciplineDetail] = Field(default=[], description="Список ФОС материалов")
    practic_programs: list[str] = Field(default=[], description="Список программ практик")
    methodical_materials: list[DisciplineDetail] = Field(default=[], description="Список методических материалов")

    gia_program: bool = Field(..., description="Наличие раздела 'ГИА'")
    education_program_vosp: bool = Field(..., description="Наличие раздела 'Рабочая программа воспитания'")
    curriculum_plan: bool = Field(..., description="Наличие Календарного плана воспитательной работы")

class WebParsingService:

    # получает div с классом col-md-9 col-md-pull-3 content bvi-speech в котором вся инфа которая нам нужна
    def _get_main_div(self, soup: BeautifulSoup) -> tuple[str, str]:
       
        all_div = soup.find('div', class_='col-md-9 col-md-pull-3 content bvi-speech')
    
        if all_div:
            divs = all_div.find_all('div', class_='desc')
            
            # print(divs) 

        
    def __init__(self, url: str, curriculum_file: str = "plan.xml"):
        self.url = url
        self.curriculum_file = curriculum_file
    
    # Парсит страницу в одном цикле и возвращает список объектов для каждого года набора
    def parse_by_year(self) -> List[Dict[str, Any]]:
        logger.info("Start parsing URL %s", self.url)
        response = requests.get(self.url)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, "html.parser")
        logger.info("Page loaded, length=%s", len(response.text))
        
        # Получаем основной div с контентом
        main_div = soup.find('div', class_='col-md-9 col-md-pull-3 content bvi-speech')
        if not main_div:
            logger.error("Main div not found")
            return []
        
        # Парсим H1
        h1_tag = soup.find('h1')
        h1_text = h1_tag.get_text(strip=True) if h1_tag else ""
        pattern = r'^(\d{2}\.\d{2}\.\d{2})\s+(.+?)\s+\(приём\s+(.+)\)$'
        match = re.match(pattern, h1_text)
        
        discipline_code = match.group(1) if match else ""
        specialty = match.group(2) if match else h1_text
        years = [year.strip() for year in match.group(3).split(',')] if match else []
        
        # Инициализируем результат для каждого года
        result_by_year = {year: {
            "specialty": specialty,
            "discipline_code": discipline_code,
            "curriculum_year": year,
            "lvl_education": "",
            "form_education": "",
            "education_program": False,
            "calendar_graphic": False,
            "education_plan": False,
            "gia_program": False,
            "education_program_vosp": False,
            "curriculum_plan": False,
            "working_programs": [],      
            "fos_materials": [],         
            "practic_programs": [],      
            "methodical_materials": []   
        } for year in years}
        
        # Получаем все div с классом desc
        desc_divs = main_div.find_all('div', class_='desc')
        
        # Переменные для отслеживания текущего раздела и года
        current_section = None
        current_year = None
        
        # Один цикл прохода по всем div.desc
        for div in desc_divs:
            text = div.get_text(strip=True)
            div_id = div.get('id')
            
            # Отладка: выводим информацию о каждом div
            logger.debug(f"Processing div: id={div_id}, text={text[:50]}...")
            
            # Если это div с id - это заголовок раздела
            if div_id:
                # Определяем тип раздела по id
                if div_id == 'op':
                    current_section = 'education_program'
                    for year in years:
                        result_by_year[year]['education_program'] = True
                    logger.info(f"Found section: {div_id} - Образовательная программа")
                elif div_id == 'kug':
                    current_section = 'calendar_graphic'
                    for year in years:
                        result_by_year[year]['calendar_graphic'] = True
                    logger.info(f"Found section: {div_id} - Календарный график")
                elif div_id == 'up':
                    current_section = 'education_plan'
                    for year in years:
                        result_by_year[year]['education_plan'] = True
                    logger.info(f"Found section: {div_id} - Учебный план")
                elif div_id == 'gia':
                    current_section = 'gia_program'
                    for year in years:
                        result_by_year[year]['gia_program'] = True
                    logger.info(f"Found section: {div_id} - ГИА")
                elif div_id == 'rpv':
                    current_section = 'education_program_vosp'
                    for year in years:
                        result_by_year[year]['education_program_vosp'] = True
                    logger.info(f"Found section: {div_id} - Рабочая программа воспитания")
                elif div_id == 'pvr':
                    current_section = 'curriculum_plan'
                    for year in years:
                        result_by_year[year]['curriculum_plan'] = True
                    logger.info(f"Found section: {div_id} - Календарный план воспитательной работы")
                elif div_id == 'rpd':
                    current_section = 'working_programs'
                    current_year = None
                    logger.info(f"Found section: {div_id} - Рабочие программы дисциплин")
                elif div_id == 'fos':
                    current_section = 'fos_materials'
                    current_year = None
                    logger.info(f"Found section: {div_id} - ФОС материалы")
                elif div_id == 'prak':
                    current_section = 'practic_programs'
                    current_year = None
                    logger.info(f"Found section: {div_id} - Практики")
                elif div_id == 'mm':
                    current_section = 'methodical_materials'
                    current_year = None
                    logger.info(f"Found section: {div_id} - Методические материалы")
                continue
            
            # Если это div без id - это контент
            if not div_id:
                # Если мы в каком-то разделе, собираем данные с группировкой по годам
                if current_section in ['working_programs', 'fos_materials', 'methodical_materials', 'practic_programs']:
                    logger.debug(f"Collecting content for {current_section}: {text}")
                    
                    # Проверяем, является ли текст годом набора
                    year_match = re.match(r'^Приём\s+(\d{4})$', text)
                    if year_match:
                        current_year = year_match.group(1)
                        logger.info(f"Found year: {current_year} for section {current_section}")
                    elif current_year and text:
                        logger.debug(f"Adding item for year {current_year}: {text}")
                        # Для практик - просто добавляем строку
                        if current_section == 'practic_programs':
                            if text not in result_by_year[current_year][current_section]:
                                result_by_year[current_year][current_section].append(text)
                                logger.info(f"Added practic: {text}")
                        else:
                            # Для рабочих программ, ФОС и методических материалов - создаем DisciplineDetail
                            code_match = re.match(r'^([A-Z0-9\.\(\)]+)\s+(.+)$', text)
                            if code_match:
                                discipline_code_value = code_match.group(1)
                                discipline_name = code_match.group(2)
                            else:
                                discipline_code_value = ""
                                discipline_name = text
                            
                            discipline_detail = {
                                "discipline_name": discipline_name,
                                "discipline_code": discipline_code_value
                            }
                            
                            # Проверяем на дубликаты по коду дисциплины
                            existing_codes = [d.get('discipline_code') for d in result_by_year[current_year][current_section]]
                            if discipline_code_value not in existing_codes:
                                result_by_year[current_year][current_section].append(discipline_detail)
                                logger.info(f"Added discipline: {discipline_code_value} - {discipline_name}")
                
                # Собираем уровень образования и форму обучения
                if 'Уровень образования' in text:
                    p_tags = div.find_all('p')
                    if len(p_tags) >= 2:
                        lvl_value = p_tags[1].get_text(strip=True)
                    else:
                        next_div = div.find_next_sibling('div', class_='desc', id=False)
                        lvl_value = next_div.get_text(strip=True) if next_div else ""
                    for year in years:
                        result_by_year[year]['lvl_education'] = lvl_value
                    logger.info(f"Found education level: {lvl_value}")
                
                if 'Форма обучения' in text:
                    p_tags = div.find_all('p')
                    if len(p_tags) >= 2:
                        form_value = p_tags[1].get_text(strip=True)
                    else:
                        next_div = div.find_next_sibling('div', class_='desc', id=False)
                        form_value = next_div.get_text(strip=True) if next_div else ""
                    for year in years:
                        result_by_year[year]['form_education'] = form_value
                    logger.info(f"Found education form: {form_value}")
        
        # Преобразуем в список
        results = [result_by_year[year] for year in years]
        
        logger.info("Parsed %d years", len(results))
        for result in results:
            logger.info("  Year %s: %d working programs, %d FOS, %d practic, %d methodical",
                    result['curriculum_year'], 
                    len(result['working_programs']), 
                    len(result['fos_materials']),
                    len(result['practic_programs']),
                    len(result['methodical_materials']))
        
        return results
    
    #validation based on pydantic2
    def parse_and_validate_all(self) -> List[CurriculumModel]:
        results = self.parse_by_year()
        models = []
        for data in results:
            try:
                models.append(CurriculumModel.model_validate(data))
            except Exception as e:
                logger.error(f"Validation error for year {data['curriculum_year']}: {e}")
        return models
        
        

if __name__ == "__main__":
    service = WebParsingService("https://mauniver.ru/sveden/education/op/42842#prak")

    # H1 parsing/cutting test
    # print(f"discipline_code: {result['discipline_code']}")
    # print(f"specialty: {result['specialty']}")
    # print(f"curriculum_year: {result['curriculum_year']}")

    # Парсим данные
    results = service.parse_by_year()
    
    for result in results:
        print(f"\nГод набора: {result['curriculum_year']} ")
        print(f"Специальность: {result['specialty']}")
        print(f"Код: {result['discipline_code']}")
        print(f"Уровень образования: {result['lvl_education']}")
        print(f"Форма обучения: {result['form_education']}")
        print(f"Наличие разделов:")
        print(f"  - Образовательная программа: {result['education_program']}")
        print(f"  - Календарный график: {result['calendar_graphic']}")
        print(f"  - Учебный план: {result['education_plan']}")
        print(f"  - ГИА: {result['gia_program']}")
        print(f"  - Рабочая программа воспитания: {result['education_program_vosp']}")
        print(f"  - Календарный план воспитательной работы: {result['curriculum_plan']}")
        
        print(f"\nРабочих программ: {len(result['working_programs'])}")
        if result['working_programs']:
            print("  Примеры:")
            for prog in result['working_programs'][:5]:
                print(f"    - {prog['discipline_code']}: {prog['discipline_name']}")
        
        print(f"\nФОС материалов: {len(result['fos_materials'])}")
        if result['fos_materials']:
            print("  Примеры:")
            for fos in result['fos_materials'][:3]:
                print(f"    - {fos['discipline_code']}: {fos['discipline_name']}")
        
        print(f"\nПрактик: {len(result['practic_programs'])}")
        if result['practic_programs']:
            print("  Примеры:")
            for p in result['practic_programs'][:3]:
                print(f"    - {p}")
        
        print(f"\nМетодических материалов: {len(result['methodical_materials'])}")
        if result['methodical_materials']:
            print("  Примеры:")
            for mm in result['methodical_materials'][:3]:
                print(f"    - {mm['discipline_code']}: {mm['discipline_name']}")
    

    
    