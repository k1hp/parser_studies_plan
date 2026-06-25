import os
from datetime import datetime
from typing import Any, List, Optional

from fpdf import FPDF

from src.schemas.response_schemas import ApiResponseSchema


class PDFReport(FPDF):
    """Класс для генерации PDF-отчёта на основе данных учебного плана."""

    def __init__(self, data: ApiResponseSchema, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = data
        self.set_auto_page_break(auto=True, margin=15)

        # Путь к файлу шрифта (должен быть добавлен в проект)
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "DejaVuSans.ttf")
        if os.path.exists(font_path):
            self.add_font("DejaVu", "", font_path, uni=True)
            self.font_name = "DejaVu"
        else:
            # fallback – если шрифт не найден, используем стандартный (не поддерживает кириллицу)
            self.font_name = "Helvetica"

    def header(self):
        self.set_font(self.font_name, size=12)
        self.cell(0, 10, "Отчет по учебному плану", ln=True, align="C")
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font(self.font_name, size=8)
        self.cell(0, 10, f"Страница {self.page_no()}", align="C")

    def generate(self) -> bytes:
        """Сгенерировать PDF и вернуть его в виде байтов."""
        self.add_page()
        self._render_main_info()
        self._render_statuses()
        self._render_table("Рабочие программы дисциплин", self.data.working_programs)
        self._render_table("ФОС материалы", self.data.fos_materials)
        self._render_table("Методические материалы", self.data.methodical_materials)
        self._render_practices()
        self._render_footer()
        return self.output()

    def _render_main_info(self):
        """Блок основной информации."""
        self.set_font(self.font_name, size=11)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, "Основная информация", ln=True, fill=True)
        self.ln(2)

        fields = [
            ("Специальность", self.data.specialty),
            ("Код дисциплины", self.data.discipline_code),
            ("Год набора", self.data.curriculum_year),
            ("Уровень образования", self.data.lvl_education),
            ("Форма обучения", self.data.form_education),
        ]

        for label, value in fields:
            self.set_font(self.font_name, size=10)
            self.cell(50, 6, label + ":", border=0)
            self.set_font(self.font_name, size=10)
            self.cell(0, 6, str(value or "-"), border=0, ln=True)
        self.ln(4)

    def _render_statuses(self):
        """Блок наличия разделов."""
        self.set_font(self.font_name, size=11)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, "Наличие разделов в учебном плане", ln=True, fill=True)
        self.ln(2)

        statuses = [
            ("Образовательная программа", self.data.education_program),
            ("Календарный учебный график", self.data.calendar_graphic),
            ("Учебный план", self.data.education_plan),
            ("ГИА", self.data.gia_program),
            ("Рабочая программа воспитания", self.data.education_program_vosp),
            ("Календарный план воспитательной работы", self.data.curriculum_plan),
        ]

        for label, value in statuses:
            self.set_font(self.font_name, size=10)
            self.cell(80, 6, label + ":", border=0)
            status_text = "Есть" if value else "Нет"
            self.set_font(self.font_name, size=10)
            self.cell(0, 6, status_text, border=0, ln=True)
        self.ln(4)

    def _render_table(self, title: str, items: List[Any]):
        """Отрисовка таблицы с дисциплинами (код + название)."""
        if not items:
            self.set_font(self.font_name, size=10)
            self.cell(0, 6, f"Нет данных о {title.lower()}", ln=True)
            self.ln(2)
            return

        self.set_font(self.font_name, size=11)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, title, ln=True, fill=True)
        self.ln(2)

        # Заголовки таблицы
        self.set_font(self.font_name, size=10, style="B")
        self.set_fill_color(200, 200, 200)
        self.cell(40, 8, "Код дисциплины", border=1, fill=True)
        self.cell(0, 8, "Название дисциплины", border=1, fill=True, ln=True)

        self.set_font(self.font_name, size=10)
        fill = False
        for item in items:
            code = getattr(item, "discipline_code", None) or "-"
            name = getattr(item, "discipline_name", "")
            # Разбиваем название, если оно длинное
            self.cell(40, 6, code, border=1, fill=fill)
            # Используем multi_cell для переноса длинных названий
            x = self.get_x()
            y = self.get_y()
            self.multi_cell(0, 6, name, border=1, fill=fill)
            # Перемещаем курсор на следующую строку
            self.set_y(y + 6)
            self.set_x(x + 40)  # возвращаемся к началу следующей строки
            fill = not fill
        self.ln(4)

    def _render_practices(self):
        """Список программ практик."""
        practices = self.data.practic_programs or []
        self.set_font(self.font_name, size=11)
        self.set_fill_color(240, 240, 240)
        self.cell(0, 8, "Программы практик", ln=True, fill=True)
        self.ln(2)

        if not practices:
            self.set_font(self.font_name, size=10)
            self.cell(0, 6, "Нет данных о программах практик", ln=True)
        else:
            self.set_font(self.font_name, size=10)
            for program in practices:
                self.cell(5, 6, "-", border=0)
                self.multi_cell(0, 6, program)
        self.ln(4)

    def _render_footer(self):
        """Нижний колонтитул с датой и подписью."""
        self.set_y(-30)
        self.set_font(self.font_name, size=9)
        current_date = datetime.now().strftime("%d.%m.%Y в %H:%M")
        self.cell(0, 6, f"Отчет создан автоматически {current_date}", align="C")
        self.ln(4)
        self.cell(0, 6, "Система проверки учебных планов", align="C")


class PDFService:
    """Сервис для генерации PDF-отчётов."""

    def __init__(self, template_dir=None):
        # template_dir больше не нужен, оставлен для совместимости
        pass

    def create_pdf(self, data: ApiResponseSchema, output_path: Optional[str] = None) -> bytes:
        """
        Создать PDF-отчёт на основе данных и вернуть его в виде байтов.
        Если указан output_path, файл будет сохранён на диск.
        """
        pdf = PDFReport(data)
        pdf_content = pdf.generate()
        if output_path:
            with open(output_path, "wb") as f:
                # noinspection PyTypeChecker
                f.write(pdf_content)
        return pdf_content

    def create_html(self, data: ApiResponseSchema, output_path: Optional[str] = None) -> bytes:
        """
        Метод сохранён для совместимости, но не реализован.
        Возвращает пустую строку (или можно выбросить NotImplementedError).
        """
        # Если нужен HTML, его можно создать отдельно, но в данной версии не поддерживается
        return b""