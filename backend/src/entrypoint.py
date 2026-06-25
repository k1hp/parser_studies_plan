from typing import List, Literal
import asyncio
import json
import redis
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, Depends, APIRouter, Response, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import HTTPException
from fastapi.openapi.utils import get_openapi

from src.config import WEEK, RETRY_DELAY
from src.config import ROOT_ADDITION_PATH
from src.dependencies import get_analyze_service, get_pdf_service, get_smb_file_manager
from src.schemas.response_schemas import ApiResponseSchema, BatchCompareResponse
from src.schemas.web_schemas import CollectAndCompareRequest
from src.services.analyze_service import AnalyzeService
from src.services.file_manager import SMBFileManager
from src.utils import applogger
from src.services.pdf_service import PDFService
from src.utils import generate_openapi_path
from src.services.parser_links_service import refresh_redis, REDIS_HOST, REDIS_PORT

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(scheduler_loop())
    yield

app = FastAPI(
    docs_url="/docs",
    openapi_url=generate_openapi_path(),
    lifespan=lifespan
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

    clean_path = ROOT_ADDITION_PATH.replace('"', '').replace("'", "").strip("/")

    base_url = f"/{clean_path}" if clean_path else "/"

    openapi_schema["servers"] = [{"url": str(base_url)}]


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
async def analyze_many(
    report_format: REPORT_FORMATS,
    files: list[UploadFile] = File(...),
    analyze_service: AnalyzeService = Depends(get_analyze_service),
    pdf_service: PDFService = Depends(get_pdf_service),
):
    file_contents: list[tuple[str, bytes]] = []
    for f in files:
        content = await f.read()
        file_contents.append((f.filename or "unknown", content))

    batch: BatchCompareResponse = analyze_service.analyze_batch(file_contents)

    if report_format == "json":
        return batch

    # for html/pdf — объединяем ok результаты в один отчёт
    ok_results = [r for r in batch.results if r.status == "ok" and r.data is not None]
    if not ok_results:
        raise HTTPException(400, "Ни один файл не удалось сравнить")

    if report_format == "html":
        html_parts = []
        for r in ok_results:
            html_parts.append(f'<h2>{r.filename} ({r.match_score:.0f}% match)</h2>')
            html_parts.append(f'<p>URL: {r.matched_url}</p>')
            html_parts.append(pdf_service.create_html(r.data))
        combined = '<!DOCTYPE html><html><head><meta charset="utf-8"><style>body{font-family:Arial;max-width:900px;margin:0 auto;padding:20px}h2{border-top:2px solid #333;padding-top:20px;margin-top:30px}</style></head><body>' + ''.join(html_parts) + '</body></html>'
        return Response(content=combined, media_type="text/html")

    if report_format == "pdf":
        pdf_bytes = pdf_service.create_pdf(ok_results[0].data)
        return Response(content=pdf_bytes, media_type="application/pdf")


@router.post("/collect-and-compare")
def collect_and_compare(
    req: CollectAndCompareRequest,
    analyze_service: AnalyzeService = Depends(get_analyze_service),
    file_manager: SMBFileManager = Depends(get_smb_file_manager),
):
    # 1. Собираем все .plx/.xml файлы из SMB-пути, указанного в .env
    try:
        file_paths = file_manager.get_files_in_directory(recursive=True)
    except Exception as e:
        raise HTTPException(400, f"Не удалось подключиться к SMB: {e}")

    if not file_paths:
        raise HTTPException(400, "Файлы .plx/.xml не найдены в указанной SMB-директории")

    # 2. Читаем файлы по одному, фильтруем по выбранным программам.
    #    Как только все программы нашли хотя бы один файл — останавливаемся.
    from rapidfuzz import fuzz

    selected = {n.lower().strip() for n in req.program_names}
    remaining = set(selected)  # программы, для которых ещё не нашли файл

    matched_files: list[tuple[str, bytes]] = []
    for path in file_paths:
        # ранний выход: все программы покрыты
        if not remaining:
            break

        try:
            content = file_manager.get_one_content(path)
            if content is None:
                continue
        except Exception:
            continue

        dir_name = _quick_direction_name(content)
        if not dir_name:
            matched_files.append((path.split("/")[-1], content))
            continue

        # проверяем fuzzy match — только против оставшихся программ
        best = 0.0
        best_prog = None
        dir_lower = dir_name.lower()
        for s in remaining:
            score = max(fuzz.ratio(dir_lower, s), fuzz.partial_ratio(dir_lower, s))
            if score > best:
                best = score
                best_prog = s
        if best >= 60:
            matched_files.append((path.split("/")[-1], content))
            remaining.discard(best_prog)

    if not matched_files:
        raise HTTPException(400, "Ни один файл не соответствует выбранным программам")

    file_manager.disconnect()

    # 3. Сравниваем
    batch = analyze_service.analyze_batch(matched_files)
    return batch


def _quick_direction_name(content: bytes) -> str:
    """Быстро извлекает direction_name из XML/PLX без полного парсинга."""
    import io, zipfile, xml.etree.ElementTree as ET

    try:
        if content[:2] == b'PK':
            with zipfile.ZipFile(io.BytesIO(content)) as zf:
                xml_files = [n for n in zf.namelist() if n.lower().endswith('.xml') and '__MACOSX' not in n]
                if not xml_files:
                    return ""
                content = zf.read(xml_files[0])

        for enc in ('utf-8', 'utf-16', 'windows-1251'):
            try:
                xml_str = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            return ""

        root = ET.fromstring(xml_str)
        for elem in root.iter():
            if elem.tag.endswith('ООП'):
                parent_code = elem.get('КодРодительскогоООП', '')
                name = elem.get('Название', '')
                if not parent_code:
                    return name.strip()
                # если есть родитель — это профиль, ищем родительское название
                profile = name
                # ищем родительский ООП
                for e in root.iter():
                    if e.tag.endswith('ООП') and e.get('Код', '') == parent_code:
                        parent_name = e.get('Название', '')
                        if parent_name and profile:
                            return f"{parent_name.strip()}, {profile.strip()}"
                        return (parent_name or profile).strip()
                return profile.strip()
        return ""
    except Exception:
        return ""


@router.get("/hierarchy")
def get_hierarchy():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    try:
        raw = r.get("hierarchy")
    except redis.ResponseError:
        r.delete("hierarchy")
        raise HTTPException(503, "Данные ещё не собраны. Вызовите /api/refresh-links")
    if not raw:
        raise HTTPException(503, "Данные ещё не собраны. Вызовите /api/refresh-links")
    return json.loads(raw)


@router.get("/status")
def api_status():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    result = {"api": "ok"}

    for key in ("flat_mapping", "hierarchy"):
        try:
            raw = r.get(key)
        except redis.ResponseError:
            r.delete(key)
            result[key] = "error: wrong type, deleted"
            continue
        if raw is None:
            result[key] = "missing"
            continue
        try:
            data = json.loads(raw)
            if key == "flat_mapping":
                result[key] = f"ok ({len(data)} programs)"
            else:
                inst_count = len(data.get("institutes", {}))
                result[key] = f"ok ({inst_count} institutes)"
        except json.JSONDecodeError:
            result[key] = "error: invalid json"

    return result


_refresh_lock = asyncio.Lock()
_refresh_running = False


def _run_refresh():
    global _refresh_running
    try:
        result = refresh_redis()
        applogger.info(f"Refresh ok: {result}")
    except Exception as e:
        applogger.error(f"Refresh failed: {e}")
    finally:
        _refresh_running = False


async def _start_refresh():
    global _refresh_running
    if _refresh_running:
        return
    _refresh_running = True
    await asyncio.to_thread(_run_refresh)


async def scheduler_loop():
    while True:
        await asyncio.sleep(WEEK)
        while True:
            try:
                await _start_refresh()
                break
            except asyncio.CancelledError:
                raise
            except Exception as e:
                applogger.error(f"Scheduled refresh failed: {e}")
                applogger.info(f"Retry in {RETRY_DELAY // 3600}h")
                await asyncio.sleep(RETRY_DELAY)


@router.post("/refresh-links")
async def refresh_links(bg: BackgroundTasks):
    global _refresh_running
    if _refresh_running:
        return {"status": "already_running"}
    bg.add_task(_run_refresh)
    return {"status": "started"}


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
