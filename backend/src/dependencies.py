from fastapi import Depends

from src.services.analyze_service import AnalyzeService
from src.services.xml_parsing_service import  XmlParsingService
from src.services.web_parsing_service import WebParsingService
from src.services.pdf_service import PDFService

def get_xml_parser_service() -> XmlParsingService:
    return XmlParsingService()

def get_web_parsing_service() -> WebParsingService:
    return WebParsingService()

def get_pdf_service() -> PDFService:
    return PDFService()


def get_analyze_service(xml_service: XmlParsingService = Depends(get_xml_parser_service), web_parsing_service: WebParsingService = Depends(get_web_parsing_service)) -> AnalyzeService:
    return AnalyzeService(web_parsing_service, xml_service)