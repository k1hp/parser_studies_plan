from enum import Enum
from typing import List, Literal

from fastapi import FastAPI, UploadFile, File, Depends, APIRouter
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.dependencies import get_analyze_service
from src.schemas.response_schemas import ApiResponseSchema
from src.services.analyze_service import AnalyzeService
from src.utils import applogger

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

REPORT_FORMATS = Literal["json", "html", "pdf"]


@router.post("/compare/{report_format}")
async def analyze(url: str, report_format: REPORT_FORMATS, file: UploadFile = File(...),
            analyze_service: AnalyzeService = Depends(get_analyze_service)):
    # TODO валидация url
    content = await file.read()
    applogger.debug(f"Analyzing {url}")
    applogger.debug(type(content))
    applogger.debug(content)
    response: ApiResponseSchema = analyze_service.analyze_one(url, content)
    if report_format == "json":
        return response
    elif report_format == "pdf":
        # передаешь response в твой конвертер pdf и потом возвращаешь сюда файл
        return ...


@router.post("/compare/files/{report_format}")
def analyze_many(report_format: REPORT_FORMATS, files: List[UploadFile]):
    ...

app.include_router(router)

# if __name__ == "__main__":
#
#     uvicorn.run(app, host="0.0.0.0", port=8000)
