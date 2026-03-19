import jinja2

# Загрузка шаблона из файла
with open('page.html', 'r', encoding='utf-8') as f:
    template_str = f.read()

template = jinja2.Template(template_str)

# Тестовые данные для переменных
test_data = {
    'verification_date': '19 марта 2026 г.',
    'curriculum_file': 'plan.pdf',
    'site_url': 'https://example.com',
    'specialty': 'Информатика',
    'curriculum_year': '2023',
    'lvl_education': 'Бакалавриат',
    'form_education': 'Очная',
    'education_program': True,
    'calendar_graphic': False,
    'curriculum_plan': True,
    'gia_program': False,
    'education_program_vosp': True,
    'education_plan_vosp': False,
    'missing_programs': ['Математика', 'Физика'],
    'missing_fos': ['ФОС1'],
    'missing_programs_practic': [],
    'missing_methodical_materials': ['Методичка1', 'Методичка2']
}

# Рендеринг шаблона
rendered_html = template.render(**test_data)

# Сохранение в файл для просмотра в браузере
with open('output.html', 'w', encoding='utf-8') as f:
    f.write(rendered_html)

print("HTML сохранен в output.html. Откройте файл в браузере для проверки отображения.")