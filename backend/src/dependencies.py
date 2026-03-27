from fastapi import Depends

from backend.src.services.analyze_service import AnalyzeService
from backend.src.services.xml_parsing_service import WebParsingService, XmlParsingService


def get_xml_parser_service() -> XmlParsingService:
    return XmlParsingService()

def get_web_parsing_service() -> WebParsingService:
    return WebParsingService()

def get_analyze_service(xml_service: XmlParsingService = Depends(get_xml_parser_service), web_parsing_service: WebParsingService = Depends(get_web_parsing_service)) -> AnalyzeService:
    return AnalyzeService(web_parsing_service, xml_service)