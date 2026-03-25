from enum import Enum
from typing import List, Literal

from fastapi import FastAPI, UploadFile, File, Depends, APIRouter
import uvicorn

from src.dependencies import get_analyze_service
from src.services.analyze_service import AnalyzeService

app = FastAPI()
router = APIRouter(prefix="/api")

REPORT_FORMATS = Literal["json", "html", "pdf"]


@router.post("/compare/{report_format}")
def analyze(url: str, report_format: REPORT_FORMATS, file: UploadFile = File(...),
            analyze_service: AnalyzeService = Depends(get_analyze_service)):
    # TODO валидация url
    # response: ... = analyze_service.analyze_one()
    ...


@router.post("/compare/files/{report_format}")
def analyze_many(report_format: REPORT_FORMATS, files: List[UploadFile]):
    ...


if __name__ == "__main__":
    app.include_router(router)

    uvicorn.run(app, host="0.0.0.0", port=8001)
