from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from weasyprint.css.validation.properties import direction
from backend.src.schemas.response_schemas import ApiResponseSchema

class PDFService:
    def __init__(self, template_dir='templates'):
        self.env = Environment(loader=FileSystemLoader(template_dir))
        self.template_name = "report_template.html"

    def create_pdf(self, data: ApiResponseSchema, output_path: str = None) -> bytes:
        # if isinstance(data, list):
            # template = self.env.get_template('comparison_template.html')
            # html_out = template.render(errors=data)
        # else:
        template = self.env.get_template('report_template.html')
        html_out = template.render(
            specialty=data.specialty,
            discipline_code=data.discipline_code,
            curriculum_year=data.curriculum_year,
            education_program=data.education_program,
            lvl_education=data.lvl_education,
            form_education=data.form_education,
            calendar_graphic=data.calendar_graphic,
            education_plan=data.education_plan,

            working_programs=data.working_programs,
            fos_materials=data.fos_materials,
            practic_programs=data.practic_programs,
            methodical_materials=data.methodical_materials,

            gia_program=data.gia_program,
            education_program_vosp=data.education_program_vosp,
            curriculum_plan=data.curriculum_plan,

            disciplines=data.working_programs
        )

        return HTML(string=html_out).write_pdf(target=output_path)