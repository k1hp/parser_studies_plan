from typing import List, Literal

from fastapi import FastAPI, UploadFile, File, Depends, APIRouter, Response
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import HTTPException
from fastapi.openapi.utils import get_openapi

from src.config import ROOT_ADDITION_PATH
from src.dependencies import get_analyze_service, get_pdf_service
from src.schemas.response_schemas import ApiResponseSchema
from src.services.analyze_service import AnalyzeService
from src.utils import applogger
from src.services.pdf_service import PDFService
from src.utils import generate_openapi_path

app = FastAPI(
    docs_url="/docs",
    openapi_url=generate_openapi_path()
)
router = APIRouter(prefix="/api")

ALL_FORMATS = Literal["json", "html", "pdf"]
REPORT_FORMATS = Literal["json", "html", "pdf"]


#
def custom_openapi():
    """
    Функция для динамической подмены списка серверов в Swagger UI
    :return:
    """
    # Если схема уже была сгенерирована ранее, отдаем её из кэша
    if app.openapi_schema:
        return app.openapi_schema

    # Генерируем стандартную схему
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Читаем переменную окружения (значение из вашего .env файла)
    # Если переменная не задана, префикс будет пустым ""


    # Принудительно жестко прописываем правильный базовый URL для Swagger
    # Теперь все curl-запросы будут строиться от http://localhost/checkplans
    openapi_schema["servers"] = [{"url": "/" + ROOT_ADDITION_PATH.strip("/")}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


# Переопределяем стандартный генератор схемы FastAPI на наш кастомный
app.openapi = custom_openapi

@router.get("/ping")
async def ping():
    return "pong"


@router.post("/compare/{report_format}")
async def analyze(url: str, report_format: ALL_FORMATS, file: UploadFile = File(...),
            analyze_service: AnalyzeService = Depends(get_analyze_service), pdf_service: PDFService = Depends(get_pdf_service)):
    # TODO валидация url
    if not file.filename.endswith((".xml", ".plx")):
        raise HTTPException(status_code=400, detail="File format not supported")
    content = await file.read()
    applogger.debug(f"Analyzing {url}")
    # applogger.debug(type(content))
    # applogger.debug(content)
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
        # передаешь response в твой конвертер pdf и потом возвращаешь сюда файл
        converted_content = pdf_service.create_pdf(response)

        return Response(
            content=converted_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="report.pdf"'
            }
        )

@router.post("/convert/{report_format}")
def convert_report(report_format: REPORT_FORMATS, data: ApiResponseSchema, pdf_service: PDFService = Depends(get_pdf_service)):
    if report_format == "html":
        converted_content = pdf_service.create_html(data)

        return Response(
            content=converted_content,
            media_type="text/html",
            headers={
                "Content-Disposition": 'attachment; filename="report.html"'
            }
        )

    elif report_format == "pdf":
        converted_content = pdf_service.create_pdf(data)

        return Response(
            content=converted_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="report.pdf"'
            }
        )



@router.post("/compare/files/{report_format}")
def analyze_many(report_format: REPORT_FORMATS, ):
    ...

app.include_router(router)
# origins = [
#     "http://127.0.0.1:80",
#     "http://127.0.0.1:8080",
#     "http://127.0.0.1:8000",
# ]
#
# # CORS
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=origins,
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
#     expose_headers=["*"]  # for file download
# )

# if __name__ == "__main__":
#
#     uvicorn.run(app, host="0.0.0.0", port=8000)
