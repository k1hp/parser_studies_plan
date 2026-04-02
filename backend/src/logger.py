import logging
from typing import List, Dict, Any
from backend.src.schemas.web_schemas import CurriculumModel, DisciplineDetail

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def print_results_as_logging(results: List[Dict[str, Any]]) -> None:
    """Выводит результаты парсинга через логирование"""
    for result in results:
        logger.info("=" * 80)
        logger.info(f"Год набора: {result['curriculum_year']}")
        logger.info(f"Специальность: {result['specialty']}")
        logger.info(f"Код: {result['discipline_code']}")
        logger.info(f"Уровень образования: {result['lvl_education']}")
        logger.info(f"Форма обучения: {result['form_education']}")
        logger.info("Наличие разделов:")
        logger.info(f"  - Образовательная программа: {result['education_program']}")
        logger.info(f"  - Календарный график: {result['calendar_graphic']}")
        logger.info(f"  - Учебный план: {result['education_plan']}")
        logger.info(f"  - ГИА: {result['gia_program']}")
        logger.info(f"  - Рабочая программа воспитания: {result['education_program_vosp']}")
        logger.info(f"  - Календарный план воспитательной работы: {result['curriculum_plan']}")
        
        logger.info(f"Рабочих программ: {len(result['working_programs'])}")
        if result['working_programs']:
            logger.info("  Примеры:")
            for prog in result['working_programs'][:5]:
                logger.info(f"    - {prog['discipline_code']}: {prog['discipline_name']}")
        
        logger.info(f"ФОС материалов: {len(result['fos_materials'])}")
        if result['fos_materials']:
            logger.info("  Примеры:")
            for fos in result['fos_materials'][:3]:
                logger.info(f"    - {fos['discipline_code']}: {fos['discipline_name']}")
        
        logger.info(f"Практик: {len(result['practic_programs'])}")
        if result['practic_programs']:
            logger.info("  Примеры:")
            for p in result['practic_programs'][:3]:
                logger.info(f"    - {p}")
        
        logger.info(f"Методических материалов: {len(result['methodical_materials'])}")
        if result['methodical_materials']:
            logger.info("  Примеры:")
            for mm in result['methodical_materials'][:3]:
                logger.info(f"    - {mm['discipline_code']}: {mm['discipline_name']}")
        logger.info("=" * 80)