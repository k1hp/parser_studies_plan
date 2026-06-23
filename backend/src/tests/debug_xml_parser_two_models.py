import json
import sys
from pathlib import Path

# Добавление корневого пути проекта для импорта
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.src.services.xml_parsing_service import XmlParsingService
from backend.src.schemas.xml_schemas import ResponseModel


def main():
    # Путь к тестовому файлу (нужно указать актуальный путь)
    fixtures_dir = Path(__file__).parent / "fixtures"
    example_file = fixtures_dir / "example.plx"

    if not example_file.exists():
        print(f"Файл не найден: {example_file}")
        return

    with open(example_file, 'rb') as f:
        content = f.read()

    parser = XmlParsingService()
    response = parser.extract_from_content(content)

    if not response:
        print("Не удалось распарсить файл.")
        return

    print("РЕЗУЛЬТАТ ПАРСИНГА")
    print(f"Код направления: {response.direction_code}")
    print(f"Название направления: {response.direction_name}")
    print(f"Год начала подготовки: {response.start_year}")
    print(f"Всего дисциплин: {len(response.disciplines)}")
    print(f"Всего практик: {len(response.practices)}")

    print("\nПЕРВЫЕ 10 ДИСЦИПЛИН")
    for i, d in enumerate(response.disciplines[:10], 1):
        print(f"{i:2}. {d.discipline_name} ({d.discipline_code or '—'})")

    if len(response.disciplines) > 10:
        print(f"... и ещё {len(response.disciplines) - 10} дисциплин")

    print("\nВСЕ ПРАКТИКИ")
    if response.practices:
        for i, p in enumerate(response.practices, 1):
            print(f"{i:2}. {p.discipline_name} ({p.discipline_code or '—'})")
    else:
        print("Практики не найдены.")

    # Полный вывод в JSON
    print("\nПОЛНЫЙ JSON (сокращённый, чтобы не засорять)")
    # Можно вывести всё, но может быть много. Ограничимся первыми 5 дисциплинами и практиками.
    data = response.model_dump(mode='json')
    data['disciplines'] = data['disciplines'][:5]  # только первые 5
    data['practices'] = data['practices'][:5]
    print(json.dumps(data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()