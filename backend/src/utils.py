from loguru import logger
from backend.src.models.response_model_xml_parser import ResponseModel
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

applogger = AppLogger(level="DEBUG").get_logger()