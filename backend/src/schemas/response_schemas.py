from pydantic import BaseModel, Field

from src.schemas.xml_schemas import DisciplineDetail


class SectionResult(BaseModel):
    matched: list[DisciplineDetail] = Field(default_factory=list)
    missing_on_site: list[DisciplineDetail] = Field(default_factory=list)
    missing_in_xml: list[DisciplineDetail] = Field(default_factory=list)


class FlagsResult(BaseModel):
    education_program: bool = False
    calendar_graphic: bool = False
    education_plan: bool = False
    gia_program: bool = False
    education_program_vosp: bool = False
    curriculum_plan: bool = False


class ApiResponseSchema(BaseModel):
    specialty: str
    discipline_code: str
    curriculum_year: str
    lvl_education: str
    form_education: str
    flags: FlagsResult
    sections: dict[str, SectionResult] = Field(default_factory=dict)


class RefreshStatus(BaseModel):
    status: str


class FileCompareResult(BaseModel):
    filename: str
    status: str  # "ok" | "url_not_found" | "year_mismatch" | "parse_error"
    direction_name: str = ""
    match_score: float = 0.0
    matched_url: str = ""
    error: str = ""
    data: ApiResponseSchema | None = None


class BatchCompareResponse(BaseModel):
    total: int
    ok_count: int
    fail_count: int
    results: list[FileCompareResult]
