from rapidfuzz import fuzz

from src.schemas.response_schemas import (
    ApiResponseSchema, SectionResult, FlagsResult, FileCompareResult, BatchCompareResponse,
)
from src.schemas.web_schemas import CurriculumModel
from src.schemas.xml_schemas import DisciplineDetail, ResponseModel
from src.services.xml_parsing_service import XmlParsingService
from src.services.web_parsing_service import WebParsingService
from src.services.parser_links_service import find_program_url
from src.utils import applogger
from fastapi import HTTPException


class AnalyzeService:

    def __init__(self, web_parser_service: WebParsingService, xml_parser_service: XmlParsingService):
        self.web_parser_service = web_parser_service
        self.xml_parser_service = xml_parser_service

    def _match_items(
        self,
        xml_items: list[DisciplineDetail],
        web_items: list[DisciplineDetail],
    ) -> SectionResult:
        matched: list[DisciplineDetail] = []
        missing_on_site: list[DisciplineDetail] = []
        used_web_indices: set[int] = set()

        for xml_item in xml_items:
            best_idx = -1
            best_score = 0

            for i, web_item in enumerate(web_items):
                if i in used_web_indices:
                    continue

                x_code = xml_item.discipline_code or ""
                w_code = web_item.discipline_code or ""

                if x_code and w_code and (x_code in w_code or w_code in x_code):
                    best_idx = i
                    break

                score = fuzz.ratio(
                    xml_item.discipline_name.lower(),
                    web_item.discipline_name.lower(),
                )
                if score > best_score:
                    best_score = score
                    best_idx = i

            if best_idx >= 0 and (
                (xml_item.discipline_code and web_items[best_idx].discipline_code
                 and (xml_item.discipline_code in web_items[best_idx].discipline_code
                      or web_items[best_idx].discipline_code in xml_item.discipline_code))
                or best_score >= 80
            ):
                used_web_indices.add(best_idx)
                matched.append(xml_item)
            else:
                missing_on_site.append(xml_item)

        missing_in_xml = [
            w for i, w in enumerate(web_items) if i not in used_web_indices
        ]

        return SectionResult(
            matched=matched,
            missing_on_site=missing_on_site,
            missing_in_xml=missing_in_xml,
        )

    def _compare_models(
        self, web_model: CurriculumModel, xml_model: ResponseModel
    ) -> ApiResponseSchema:

        sections = {}
        section_xml_map = {
            "working_programs": xml_model.disciplines,
            "fos_materials": xml_model.disciplines,
            "practic_programs": xml_model.practices,
            "methodical_materials": xml_model.disciplines,
        }

        for key, xml_items in section_xml_map.items():
            web_items: list[DisciplineDetail] = getattr(web_model, key)
            result = self._match_items(list(xml_items), web_items)
            if result.matched or result.missing_on_site or result.missing_in_xml:
                sections[key] = result

        flags = FlagsResult(
            education_program=web_model.education_program,
            calendar_graphic=web_model.calendar_graphic,
            education_plan=web_model.education_plan,
            gia_program=web_model.gia_program,
            education_program_vosp=web_model.education_program_vosp,
            curriculum_plan=web_model.curriculum_plan,
        )

        return ApiResponseSchema(
            specialty=web_model.specialty,
            discipline_code=web_model.discipline_code,
            curriculum_year=str(web_model.curriculum_year),
            lvl_education=web_model.lvl_education,
            form_education=web_model.form_education,
            flags=flags,
            sections=sections,
        )

    def analyze_one(self, url: str, content: bytes) -> ApiResponseSchema:
        web_data = self.web_parser_service.parse_url(url)
        xml_data = self.xml_parser_service.extract_from_content(content)

        if xml_data is None:
            raise HTTPException(400, "Не удалось распарсить XML/PLX файл")

        web_model = None
        for model in web_data:
            if xml_data.start_year == int(model.curriculum_year):
                web_model = model
                break

        if web_model is None:
            raise HTTPException(
                400, f"Отсутствуют данные за {xml_data.start_year} год на сайте"
            )

        return self._compare_models(web_model, xml_data)

    def analyze_batch(
        self, files: list[tuple[str, bytes]]
    ) -> BatchCompareResponse:
        results: list[FileCompareResult] = []
        ok_count = 0
        fail_count = 0

        for filename, content in files:
            try:
                xml_data = self.xml_parser_service.extract_from_content(content)
                if xml_data is None:
                    results.append(FileCompareResult(
                        filename=filename,
                        status="parse_error",
                        error="Не удалось распарсить файл",
                    ))
                    fail_count += 1
                    continue

                url, score = find_program_url(xml_data.direction_name)
                if url is None:
                    results.append(FileCompareResult(
                        filename=filename,
                        status="url_not_found",
                        direction_name=xml_data.direction_name,
                        match_score=score,
                        error="Программа не найдена на сайте — попробуйте обновить кеш ссылок",
                    ))
                    fail_count += 1
                    continue

                web_data = self.web_parser_service.parse_url(url)
                web_model = None
                for model in web_data:
                    if xml_data.start_year == int(model.curriculum_year):
                        web_model = model
                        break

                if web_model is None:
                    results.append(FileCompareResult(
                        filename=filename,
                        status="year_mismatch",
                        direction_name=xml_data.direction_name,
                        match_score=score,
                        matched_url=url,
                        error=f"Нет данных за {xml_data.start_year} год на сайте",
                    ))
                    fail_count += 1
                    continue

                cmp = self._compare_models(web_model, xml_data)
                results.append(FileCompareResult(
                    filename=filename,
                    status="ok",
                    direction_name=xml_data.direction_name,
                    match_score=score,
                    matched_url=url,
                    data=cmp,
                ))
                ok_count += 1

            except Exception as e:
                results.append(FileCompareResult(
                    filename=filename,
                    status="parse_error",
                    error=str(e)[:300],
                ))
                fail_count += 1

        return BatchCompareResponse(
            total=len(files),
            ok_count=ok_count,
            fail_count=fail_count,
            results=results,
        )
