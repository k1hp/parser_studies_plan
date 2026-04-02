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
            direction_code=data.direction_code,
            direction_name=data.direction_name,
            start_year=data.start_year,
            disciplines=data.disciplines
        )

        return HTML(string=html_out).write_pdf(target=output_path)