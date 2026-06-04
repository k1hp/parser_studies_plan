# test_smb_to_xml_parser.py
import sys
import os
import time
import hashlib
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.src.services.file_manager import SMBFileManager
from backend.src.services.xml_parsing_service import XmlParsingService
from backend.src.utils import applogger


class SMBToXMLParserTester:
    """Тестер передачи данных из SMB в XmlParserService"""

    def __init__(self, smb_path: str, username: str, password: str):
        self.smb_manager = SMBFileManager(smb_path, username, password)
        self.xml_parser = XmlParsingService()
        self.results = []

    def print_byte_analysis(self, data: bytes, title: str = "Анализ данных"):
        """Подробный анализ байтов данных"""
        print(f"{title}")

        if not data:
            print("ДАННЫЕ ОТСУТСТВУЮТ (None или пустые)")
            return

        print(f"Общая информация:")
        print(f"   Размер данных: {len(data)} байт ({len(data) / 1024:.2f} КБ)")

        # Анализ первых 1000 байт
        sample_size = min(1000, len(data))
        sample = data[:sample_size]

        print(f"\nАнализ первых {sample_size} байт:")

        # Статистика по байтам
        null_count = sample.count(b'\x00')
        printable_count = sum(32 <= b <= 126 or b in [9, 10, 13] for b in sample)
        non_printable_count = sample_size - printable_count - null_count

        print(f"   Нулевые байты (\\x00): {null_count} ({null_count / sample_size * 100:.1f}%)")
        print(f"   Печатные символы: {printable_count} ({printable_count / sample_size * 100:.1f}%)")
        print(f"   Непечатные символы: {non_printable_count} ({non_printable_count / sample_size * 100:.1f}%)")

        # Проверка на наличие "мусора"
        has_garbage = False

        # Проверка на необычные последовательности
        if null_count > sample_size * 0.5:  # Более 50% нулевых байт
            print(f"ОБНАРУЖЕНО МНОГО НУЛЕВЫХ БАЙТОВ! Возможно, файл поврежден или это бинарные данные")
            has_garbage = True

        # Проверка на наличие BOM (Byte Order Mark)
        if data.startswith(b'\xef\xbb\xbf'):
            print(f"Обнаружен UTF-8 BOM")
        elif data.startswith(b'\xff\xfe'):
            print(f"Обнаружен UTF-16 LE BOM")
        elif data.startswith(b'\xfe\xff'):
            print(f"Обнаружен UTF-16 BE BOM")

        # Показываем первые байты в разных представлениях
        print(f"\nПервые 200 байт (HEX):")
        hex_str = ' '.join(f'{b:02x}' for b in sample[:50])
        print(f"   {hex_str}")

        print(f"\nПервые 500 байт (текст):")
        try:
            # Пробуем декодировать как UTF-8
            text_sample = sample.decode('utf-16', errors='replace')
            print(f"   {text_sample[:500]}")
        except:
            print(f"   (не удалось декодировать как UTF-16)")

        # Показываем "мусорные" символы
        if non_printable_count > 0:
            print(f"\nНайдены непечатные символы (первые 10):")
            garbage_chars = []
            for i, b in enumerate(sample[:500]):
                if b < 32 and b not in [9, 10, 13]:
                    garbage_chars.append(f"позиция {i}: \\x{b:02x}")
                    if len(garbage_chars) >= 10:
                        break
            for g in garbage_chars:
                print(f"   {g}")

        return not has_garbage

    def print_xml_analysis(self, parsed_data, file_name: str):
        """Анализ распарсенных XML данных"""
        if not parsed_data:
            print(f"\nФайл {file_name}: НЕ УДАЛОСЬ РАСПАРСИТЬ")
            return False

        print(f"Анализ XML данных из файла: {file_name}")

        print(f"\nИзвлеченные данные:")
        print(f"   Код направления: {parsed_data.direction_code or 'НЕ УКАЗАН'}")
        print(f"   Название: {parsed_data.direction_name or 'НЕ УКАЗАНО'}")
        print(f"   Год начала: {parsed_data.start_year}")
        print(f"   Количество дисциплин: {len(parsed_data.disciplines)}")

        # Проверяем дисциплины на мусор
        print(f"\nДисциплины (первые 10):")
        has_garbage = False

        for i, disc in enumerate(parsed_data.disciplines[:10], 1):
            # Проверяем название на непечатные символы
            garbage_in_name = False
            if disc.discipline_name:
                for ch in disc.discipline_name:
                    if ord(ch) < 32 and ord(ch) not in [9, 10, 13]:
                        garbage_in_name = True
                        has_garbage = True
                        break

            status = "!" if garbage_in_name else "*"
            print(f"   {status} {i}. {disc.discipline_name[:50]} (Код: {disc.discipline_code or 'Нет'})")

            if garbage_in_name:
                print(f"ОБНАРУЖЕН МУСОР В НАЗВАНИИ!")

        if has_garbage:
            print(f"\nОБНАРУЖЕН МУСОР В ДАННЫХ!")
        else:
            print(f"\nМусор в данных не обнаружен")

        return not has_garbage

    def test_single_file(self, file_path: str, show_bytes: bool = True):
        """Тест обработки одного файла"""
        print(f"ТЕСТ ОБРАБОТКИ ФАЙЛА: {os.path.basename(file_path)}")

        result = {
            'file_path': file_path,
            'file_name': os.path.basename(file_path),
            'success': False,
            'size': 0,
            'has_garbage': False,
            'parse_success': False
        }

        # 1. Получаем содержимое файла
        print(f"\n[1/3] Получение содержимого файла...")
        start_time = time.time()
        content = self.smb_manager.get_one_content(file_path)
        elapsed = time.time() - start_time

        if not content:
            print(f"Не удалось получить содержимое файла")
            return result

        result['size'] = len(content)
        print(f"Файл получен за {elapsed:.3f} сек")
        print(f"   Размер: {len(content)} байт")

        # 2. Анализ байтов
        print(f"\n[2/3] Анализ байтового содержимого...")
        has_garbage = not self.print_byte_analysis(content, f"Байтовый анализ файла {result['file_name']}")
        result['has_garbage'] = has_garbage

        if has_garbage:
            print(f"\nВНИМАНИЕ: Обнаружен мусор в байтовых данных!")

        # 3. Парсинг XML
        print(f"\n[3/3] Парсинг XML...")
        start_time = time.time()
        parsed_data = self.xml_parser.extract_from_content(content)
        elapsed = time.time() - start_time

        if parsed_data:
            result['parse_success'] = True
            print(f"XML распарсен за {elapsed:.3f} сек")

            # Анализ распарсенных данных
            parse_has_garbage = not self.print_xml_analysis(parsed_data, result['file_name'])
            result['has_garbage'] = result['has_garbage'] or parse_has_garbage
        else:
            print(f"Не удалось распарсить XML")

        result['success'] = result['parse_success'] and not result['has_garbage']

        # Итог
        print(f"ИТОГ ДЛЯ ФАЙЛА {result['file_name']}:")

        if result['success']:
            print(f"УСПЕШНО! Данные получены и распарсены корректно")
        else:
            if not result['parse_success']:
                print(f"ОШИБКА: Не удалось распарсить XML")
            if result['has_garbage']:
                print(f"ОШИБКА: В данных обнаружен мусор")

        self.results.append(result)
        return result

    def test_multiple_files(self, max_files: int = 5, show_bytes_limit: int = 1000):
        """Тест обработки нескольких файлов"""
        print(f"ТЕСТ ОБРАБОТКИ НЕСКОЛЬКИХ ФАЙЛОВ (максимум {max_files})")

        # Получаем список файлов
        all_files = self.smb_manager.get_files_in_directory()

        if not all_files:
            print("Файлы не найдены")
            return []

        print(f"\nНайдено файлов: {len(all_files)}")

        # Отбираем только непустые файлы
        non_empty_files = []
        print(f"\nПроверка файлов на пустоту...")

        for i, file_path in enumerate(all_files[:max_files * 3], 1):
            content = self.smb_manager.get_one_content(file_path)
            if content and len(content) > 0:
                non_empty_files.append(file_path)
                print(f"{i}. {os.path.basename(file_path)} - {len(content)} байт")
            else:
                print(f"{i}. {os.path.basename(file_path)} - ПУСТОЙ (пропускаем)")

            if len(non_empty_files) >= max_files:
                break

        if not non_empty_files:
            print("Нет непустых файлов для тестирования")
            return []

        print(f"\nНайдено непустых файлов: {len(non_empty_files)}")

        # Обрабатываем каждый файл
        for file_path in non_empty_files:
            self.test_single_file(file_path)

        # Выводим сводку
        self.print_summary()

        return self.results

    def test_specific_file_by_name(self, file_name: str):
        """Тест конкретного файла по имени"""
        print(f"ПОИСК ФАЙЛА: {file_name}")

        all_files = self.smb_manager.get_files_in_directory()

        if not all_files:
            print("Файлы не найдены")
            return None

        # Ищем файл
        found_file = None
        for file_path in all_files:
            if os.path.basename(file_path) == file_name:
                found_file = file_path
                break

        if not found_file:
            print(f"Файл {file_name} не найден")
            print(f"\nДоступные файлы (первые 10):")
            for f in all_files[:10]:
                print(f"   - {os.path.basename(f)}")
            return None

        print(f"Файл найден: {found_file}")

        # Проверяем что файл не пустой
        content = self.smb_manager.get_one_content(found_file)
        if not content or len(content) == 0:
            print(f"Файл {file_name} пустой, пропускаем")
            return None

        # Обрабатываем файл
        return self.test_single_file(found_file)

    def print_summary(self):
        """Вывод сводки результатов"""
        if not self.results:
            print("\nНет результатов для отображения")
            return

        print("СВОДКА РЕЗУЛЬТАТОВ")

        total = len(self.results)
        successful = sum(1 for r in self.results if r['success'])
        parse_success = sum(1 for r in self.results if r['parse_success'])
        has_garbage = sum(1 for r in self.results if r['has_garbage'])
        total_size = sum(r['size'] for r in self.results)

        print(f"\nСтатистика:")
        print(f"Обработано файлов: {total}")
        print(f"Общий размер данных: {total_size} байт ({total_size / 1024:.2f} КБ)")
        print(f"Полностью успешных: {successful}")
        print(f"Успешно распарсено: {parse_success}")
        print(f"Обнаружен мусор: {has_garbage}")

        print(f"\nДетали по файлам:")
        print(f"{'№':<3} {'Статус':<10} {'Размер':<10} {'Мусор':<8} {'Имя файла'}")

        for i, result in enumerate(self.results, 1):
            status = "OK" if result['success'] else "FAIL"
            garbage = "Да" if result['has_garbage'] else "Нет"
            size_kb = result['size'] / 1024
            print(f"{i:<3} {status:<10} {size_kb:.1f}КБ   {garbage:<8} {result['file_name']}")

        # Итоговая оценка
        print("ИТОГОВАЯ ОЦЕНКА:")

        if successful == total and parse_success == total and has_garbage == 0:
            print("Все файлы обработаны корректно, мусора не обнаружено")
        elif successful > 0:
            print(f"Успешно обработано {successful} из {total} файлов")
            if has_garbage > 0:
                print(f"Обнаружен мусор в {has_garbage} файлах")
        else:
            print("Не удалось корректно обработать ни одного файла")


def main():
    """Главная функция для запуска тестов"""

    # Конфигурация SMB
    SMB_CONFIG = {
        "smb_path": "smb://127.0.0.1/Share",
        "username": "username",
        "password": "password"
    }

    print("ТЕСТ ПЕРЕДАЧИ ДАННЫХ ИЗ SMB В XmlParserService")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Создаем тестер
    tester = SMBToXMLParserTester(
        smb_path=SMB_CONFIG["smb_path"],
        username=SMB_CONFIG["username"],
        password=SMB_CONFIG["password"]
    )

    # Выбираем режим тестирования
    print("\nВыберите режим тестирования:")
    print("1. Тест одного файла (выбор по имени)")
    print("2. Тест нескольких файлов (автоматически)")
    print("3. Тест всех непустых файлов (до 10)")

    choice = input("\nВаш выбор (1-3): ").strip()

    if choice == "1":
        file_name = input("Введите имя файла (например, 1.xml): ").strip()
        tester.test_specific_file_by_name(file_name)

    elif choice == "3":
        tester.test_multiple_files(max_files=10, show_bytes_limit=1000)

    else:  # choice == "2" или по умолчанию
        tester.test_multiple_files(max_files=5, show_bytes_limit=1000)

    print(f"\nТестирование завершено в {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


def test_all_non_empty_files():
    """Функция для автоматического тестирования всех непустых файлов"""

    SMB_CONFIG = {
        "smb_path": "smb://127.0.0.1/Share",
        "username": "username",
        "password": "password"
    }

    tester = SMBToXMLParserTester(
        smb_path=SMB_CONFIG["smb_path"],
        username=SMB_CONFIG["username"],
        password=SMB_CONFIG["password"]
    )

    # Тестируем все непустые файлы (до 15)
    results = tester.test_multiple_files(max_files=15)

    return results


if __name__ == "__main__":
    # Для автоматического теста без ввода пользователя, раскомментируйте:
    # test_all_non_empty_files()

    # Интерактивный режим
    main()