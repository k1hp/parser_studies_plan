import jinja2
from datetime import datetime

# Загрузка шаблона из файла
with open('page.html', 'r', encoding='utf-8') as f:
    template_str = f.read()

template = jinja2.Template(template_str)

# Тестовые данные для переменных
test_data = {
    'verification_date': datetime.now().strftime('%d.%m.%Y %H:%M:%S'),
    'curriculum_file': 'plan.xml',
    'site_url': 'https://mauniver.ru/sveden/education/op/43292#prak',
    'specialty': '09.03.01 Информатика и вычислительная техника. Технологии разработки веб-приложений',
    'curriculum_year': '2025',
    'lvl_education': 'Бакалавриат',
    'form_education': 'Очная',
    'education_program': True,
    'calendar_graphic': True,
    'curriculum_plan': True,
    'gia_program': False,
    'education_program_vosp': True,
    'education_plan_vosp': False,
    'missing_programs': ['Б1.В.01.05 Совр PHP- фреймворки_РПД', 
                         'Б1.В.01.06 Анализ изображений - РПД'],
    'missing_fos': ['Б1.В.01.01 Основы языка прогр JavaScript_ФОС', 
                    'Б1.О.17.09 Технология проектирования ИС ММ'],
    'missing_programs_practic': [],
    'missing_methodical_materials': ['Б1.О.10_09.03.01_ИВТ_ВП_ММ', 
                                     'Б1.О.17.05 Сети ЭВМ и телекомм_ММ']
}

# Рендеринг шаблона
rendered_html = template.render(**test_data)

# Сохранение в файл для просмотра в браузере
with open('output.html', 'w', encoding='utf-8') as f:
    f.write(rendered_html)

print("HTML сохранен в output.html. Откройте файл в браузере для проверки отображения.")