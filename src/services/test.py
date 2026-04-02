from typing import List, Dict, Any
import re
import requests
from bs4 import BeautifulSoup
import logging
from pydantic import BaseModel, Field

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

    def __init__(self, url: str, curriculum_file: str = "plan.xml"):
        self.url = url
        self.curriculum_file = curriculum_file

    def parse_by_year(self) -> List[Dict[str, Any]]:
      logger.info("Start parsing URL %s", self.url)
      response = requests.get(self.url)
      response.raise_for_status()

      soup = BeautifulSoup(response.text, "html.parser")
      logger.info("Page loaded, length=%s", len(response.text))

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

      # Инициализация результатов
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

      desc_divs = main_div.find_all('div', class_='desc')

      

      # Функция для обработки секций с дисциплинами
      def process_section(section_div: Tag, target_field: str):
        """Извлекает данные из секции (rpd, fos, prak, mm)"""
        year_links = section_div.find_all('a', class_='dotted-a')
        
        logger.info(f"Processing section {target_field}, found {len(year_links)} year links")
        
        for link in year_links:
            link_text = link.get_text(strip=True)
            year_match = re.match(r'Приём\s+(\d{4})', link_text)
            if not year_match:
                continue
            current_year = year_match.group(1)
            logger.info(f"  Found year: {current_year}")
            
            next_elem = link.find_next_sibling()
            collapse_div = None
            while next_elem:
                if next_elem.name == 'div' and 'collapse' in next_elem.get('class', []):
                    collapse_div = next_elem
                    break
                next_elem = next_elem.find_next_sibling()
            
            if collapse_div:
                links = collapse_div.find_all('a', href=True)
                logger.info(f"    Found {len(links)} discipline links for {current_year}")
                
                for idx, a in enumerate(links):
                    text = a.get_text(strip=True)
                    if not text:
                        continue
                    
                    # Показываем первые 5 ссылок для отладки
                    if idx < 5:
                        logger.info(f"      [{idx}] Original text: {text}")
                    
                    if target_field == 'practic_programs':
                        if text not in result_by_year[current_year][target_field]:
                            result_by_year[current_year][target_field].append(text)
                            logger.info(f"      Added practic: {text[:50]}")
                    else:
                        # Сначала пробуем новый улучшенный метод
                        disc_code, disc_name = self._extract_discipline_code_and_name(text)
                        
                        # Если код не найден, используем старый метод как fallback
                        if not disc_code or disc_code == text or disc_code.startswith('UNKNOWN'):
                            # Пробуем разные способы извлечения кода
                            code_match = re.match(r'^([A-Z0-9\.\(\)]+?)[_\s]', text)
                            if not code_match:
                                code_match = re.match(r'^([A-Z0-9\.\(\)]+)', text)
                            
                            if code_match:
                                disc_code = code_match.group(1)
                                disc_name = text[len(disc_code):].lstrip('_').lstrip(' ').strip()
                                if not disc_name:
                                    disc_name = text
                            else:
                                disc_code = f"UNKNOWN_{idx}"
                                disc_name = text
                        
                        disc_detail = {"discipline_name": disc_name, "discipline_code": disc_code}
                        
                        if idx < 5:
                            logger.info(f"      [{idx}] Extracted code: '{disc_code}', name: '{disc_name[:50]}'")
                        
                        existing_codes = [d.get('discipline_code') for d in result_by_year[current_year][target_field]]
                        if disc_code not in existing_codes:
                            result_by_year[current_year][target_field].append(disc_detail)
                            logger.info(f"      [{idx}] ADDED to {current_year}")
                        else:
                            logger.warning(f"      [{idx}] DUPLICATE code '{disc_code}' for {current_year}, skipping")

      # Основной цикл по всем div.desc
      for div in desc_divs:
          text = div.get_text(strip=True)
          div_id = div.get('id')

          if div_id:
              # Обработка разделов-индикаторов
              if div_id == 'op':
                  for year in years:
                      result_by_year[year]['education_program'] = True
              elif div_id == 'kug':
                  for year in years:
                      result_by_year[year]['calendar_graphic'] = True
              elif div_id == 'up':
                  for year in years:
                      result_by_year[year]['education_plan'] = True
              elif div_id == 'gia':
                  for year in years:
                      result_by_year[year]['gia_program'] = True
              elif div_id == 'rpv':
                  for year in years:
                      result_by_year[year]['education_program_vosp'] = True
              elif div_id == 'pvr':
                  for year in years:
                      result_by_year[year]['curriculum_plan'] = True
              # Обработка разделов с содержимым
              elif div_id == 'rpd':
                  logger.info("=== Processing RPD section ===")
                  process_section(div, 'working_programs')
              elif div_id == 'fos':
                  logger.info("=== Processing FOS section ===")
                  process_section(div, 'fos_materials')
              elif div_id == 'prak':
                  logger.info("=== Processing PRAK section ===")
                  process_section(div, 'practic_programs')
              elif div_id == 'mm':
                  logger.info("=== Processing MM section ===")
                  process_section(div, 'methodical_materials')
          else:
              # Уровень образования и форма обучения
              if 'Уровень образования' in text:
                  p_tags = div.find_all('p')
                  if len(p_tags) >= 2:
                      lvl_value = p_tags[1].get_text(strip=True)
                  else:
                      next_div = div.find_next_sibling('div', class_='desc', id=False)
                      lvl_value = next_div.get_text(strip=True) if next_div else ""
                  for year in years:
                      result_by_year[year]['lvl_education'] = lvl_value
              if 'Форма обучения' in text:
                  p_tags = div.find_all('p')
                  if len(p_tags) >= 2:
                      form_value = p_tags[1].get_text(strip=True)
                  else:
                      next_div = div.find_next_sibling('div', class_='desc', id=False)
                      form_value = next_div.get_text(strip=True) if next_div else ""
                  for year in years:
                      result_by_year[year]['form_education'] = form_value

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
    
    def _extract_discipline_code_and_name(self, text: str) -> tuple[str, str]:
        """
        Извлекает код дисциплины и название из текста.
        Возвращает (code, name)
        """
        text = text.strip()
        
        # Паттерны для поиска кода в начале строки
        patterns = [
            # Б1.В.01.01, Б1.О.13.01, К.М.01.01 и т.д.
            r'^([A-ZА-Я]+\d*\.?[A-ZА-Я]?\.?\d+\.?\d*\.?\d*[A-ZА-Я]?\.?\d*)(?:[_\s]|$)',
            # Коды с суффиксами _РП, _РПД, _ФОС, _ММ
            r'^([A-ZА-Я0-9\.\(\)]+?)(?:_РПД?|_ФОС|_ММ)(?:[_\s]|$)',
            # Упрощенный вариант
            r'^([A-ZА-Я0-9\.\(\)]+?)(?:[_\s]|$)'
        ]
        
        code = ""
        name = text
        
        for pattern in patterns:
            match = re.match(pattern, text)
            if match:
                code = match.group(1)
                name = text[len(code):].lstrip('_').lstrip(' ').strip()
                if not name or len(name) < 3:
                    name = text
                break
        
        # Очищаем код от суффиксов
        if code:
            for suffix in ['_РП', '_РПД', '_ФОС', '_ММ', '_РП_', '_РПД_', '_ФОС_', '_ММ_']:
                if code.endswith(suffix):
                    code = code[:-len(suffix)]
                    break
        
        # Если код не найден, но есть суффикс
        if not code:
            for suffix in ['_РП', '_РПД', '_ФОС', '_ММ']:
                if suffix in text:
                    parts = text.split(suffix)
                    if len(parts) > 0 and re.search(r'\d+\.\d+', parts[0]):
                        code = parts[0].strip()
                        name = text[len(code):].lstrip('_').lstrip(' ').strip()
                        break
        
        if not name or name == text:
            name = text
        
        return code, name
    
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
    service = WebParsingService("https://mauniver.ru/sveden/education/op/55217#prak")
    results = service.parse_by_year()
    
    for result in results:
        print(f"\nГод набора: {result['curriculum_year']}")
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