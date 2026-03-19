from fastapi import FastAPI, UploadFile, File, Depends
import uvicorn

from src.dependencies import get_analyze_service
from src.services.analyze_service import AnalyzeService

app = FastAPI()

@app.get("/analyze")
def analyze(url: str, file: UploadFile = File(...), analyze_service: AnalyzeService = Depends(get_analyze_service)):
    # TODO валидация url
    ...

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)


