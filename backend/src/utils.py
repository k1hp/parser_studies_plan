from loguru import logger

from src.config import ROOT_ADDITION_PATH
from src.schemas.xml_schemas import ResponseModel
import sys

class AppLogger:
    def __init__(self, level="INFO"):
        logger.remove()
        dev_format = (
            "<green>{time:HH:mm:ss.SSS}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
        )
        logger.add(sys.stdout, format=dev_format, level=level, colorize=True)

    def get_logger(self):
        return logger

def print_response(response: ResponseModel) -> None:
    """Выводит результаты парсинга через логирование"""
    
    applogger.debug("=" * 120)
    applogger.debug(f"\nКод направления: {response.direction_code}")
    applogger.debug(f"Название направления: {response.direction_name}")
    applogger.debug(f"Год начала обучения: {response.start_year}")
    applogger.debug(f"\nСПИСОК ДИСЦИПЛИН (всего: {len(response.disciplines)}):")
    applogger.debug("=" * 120)

    if response.disciplines:
        for i, disc in enumerate(response.disciplines, 1):
            applogger.debug(f"\n{i}. {disc.discipline_name}")
            applogger.debug(f"   Код дисциплины: {disc.discipline_code or 'Не указан'}")
        applogger.debug("-" * 100)
    else:
        applogger.debug("\n  Дисциплины не найдены")

def generate_openapi_path(addition_path: str = ROOT_ADDITION_PATH) -> str:
    clean_path = addition_path.replace('"', '').replace("'", "").strip("/")

    base_url = f"/{clean_path}" if clean_path else ""
    return base_url + "/docs/openapi.json"

applogger = AppLogger(level="DEBUG").get_logger()



if __name__ == "__main__":
    print(generate_openapi_path(ROOT_ADDITION_PATH))