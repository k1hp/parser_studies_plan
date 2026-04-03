from enum import Enum
from fastapi import FastAPI, UploadFile, File, Depends, APIRouter, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from src.dependencies import get_analyze_service, get_pdf_service
from src.schemas.response_schemas import ApiResponseSchema
from src.services.analyze_service import AnalyzeService
from src.utils import applogger
from src.services.pdf_service import PDFService

app = FastAPI()

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

router = APIRouter(prefix="/api")

class ReportFormat(str, Enum):
    JSON = "json"
    HTML = "html"
    PDF = "pdf"

@router.post("/compare/{report_format}")
async def analyze(url: str, report_format: ReportFormat, file: UploadFile = File(...),
            analyze_service: AnalyzeService = Depends(get_analyze_service), pdf_service: PDFService = Depends(get_pdf_service)):
    # TODO валидация url
    content = await file.read()
    applogger.debug(f"Analyzing {url}")
    applogger.debug(type(content))
    applogger.debug(content)
    response: ApiResponseSchema = analyze_service.analyze_one(url, content)
    if report_format == "json":
        return response

    elif report_format == "html":
        converted_content = pdf_service.create_html(response)

        return Response(
            content=converted_content,
            media_type="text/html",
            headers={
                "Content-Disposition": 'attachment; filename="report.html"'
            }
        )

    elif report_format == "pdf":
        converted_content = pdf_service.create_pdf(response)

        return Response(
            content=converted_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="report.pdf"'
            }
        )

@router.post("/compare/files/{report_format}")
async def analyze_many(report_format: ReportFormat, files: list[UploadFile]):
    ...

app.include_router(router)