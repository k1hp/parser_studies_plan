# test_smb_recursive_and_time.py
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.src.services.file_manager import SMBFileManager


class Timer:
    """Класс для измерения времени выполнения"""

    def __init__(self, name: str = "Операция"):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        print(f"\nНачало: {self.name}...")
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        elapsed = self.elapsed_time
        print(f"Завершено: {self.name}")
        print(f"   Время выполнения: {elapsed:.3f} секунд ({elapsed * 1000:.2f} мс)")

    @property
    def elapsed_time(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0


def print_separator(char="=", length=60):
    """Печать разделителя"""
    print(char * length)


def format_time(seconds: float) -> str:
    """Форматирование времени"""
    if seconds < 0.001:
        return f"{seconds * 1000000:.2f} мкс"
    elif seconds < 1:
        return f"{seconds * 1000:.2f} мс"
    elif seconds < 60:
        return f"{seconds:.3f} сек"
    else:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes} мин {secs:.1f} сек"


def test_smb_recursive_search():
    """Тест рекурсивного поиска файлов во вложенных папках с измерением времени"""

    # Конфигурация
    smb = SMBFileManager(
        smb_path="smb://127.0.0.1/Share",
        username="username",
        password="password"
    )

    print_separator("=")
    print("ТЕСТ: Рекурсивный поиск SMB файлов с измерением времени")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("=")

    # Словарь для хранения результатов
    results = {}

    # 1. Показываем структуру директорий
    print("\n1. Структура SMB шары:")
    print_separator("-")

    with Timer("Получение структуры директорий") as timer:
        smb.get_directory_structure()
    results['directory_structure'] = timer.elapsed_time

    # 2. Поиск всех файлов рекурсивно
    print("\n2. Поиск всех XML и PLX файлов (рекурсивно):")
    print_separator("-")

    with Timer("Рекурсивный поиск файлов") as timer:
        all_files = smb.get_files_in_directory(recursive=True)
    results['recursive_search_time'] = timer.elapsed_time
    results['recursive_files_count'] = len(all_files)

    if all_files:
        print(f"\nРезультаты рекурсивного поиска:")
        print(f"Найдено файлов: {len(all_files)}")
        print(f"Время поиска: {format_time(results['recursive_search_time'])}")
        print(f"Скорость: {len(all_files) / results['recursive_search_time']:.2f} файлов/сек")

        print("\n   Список найденных файлов (первые 10):")
        for i, f in enumerate(all_files[:10], 1):
            smb_path = f.replace("smb://localhost/Share/", "")
            print(f"     {i}. {smb_path}")
        if len(all_files) > 10:
            print(f"     ... и еще {len(all_files) - 10} файлов")
    else:
        print("\nФайлы не найдены")

    # 3. Поиск только в корне (без рекурсии)
    print("\n3. Поиск файлов ТОЛЬКО в корне (без рекурсии):")
    print_separator("-")

    with Timer("Поиск в корневой директории") as timer:
        root_files = smb.get_files_in_directory(recursive=False)
    results['root_search_time'] = timer.elapsed_time
    results['root_files_count'] = len(root_files)

    if root_files:
        print(f"\nРезультаты поиска в корне:")
        print(f"Найдено файлов в корне: {len(root_files)}")
        print(f"Время поиска: {format_time(results['root_search_time'])}")
        print(f"Скорость: {len(root_files) / results['root_search_time']:.2f} файлов/сек")

        print("\n   Список файлов в корне:")
        for f in root_files:
            print(f"     - {os.path.basename(f)}")
    else:
        print("\nВ корне нет файлов с нужными расширениями")

    # 4. Сравнение рекурсивного и нерекурсивного поиска
    if all_files and root_files:
        print("\n4. Сравнение производительности:")
        print_separator("-")

        # Сравнение времени
        time_diff = results['recursive_search_time'] - results['root_search_time']
        time_percent = (results['recursive_search_time'] / results['root_search_time']) * 100

        print(f"\nСравнение:")
        print(
            f"   Нерекурсивный поиск: {format_time(results['root_search_time'])} ({results['root_files_count']} файлов)")
        print(
            f"   Рекурсивный поиск:   {format_time(results['recursive_search_time'])} ({results['recursive_files_count']} файлов)")
        print(
            f"   Разница во времени:  {format_time(abs(time_diff))} ({time_percent:.1f}% от времени корневого поиска)")

        # Дополнительные файлы, найденные рекурсивно
        extra_files = results['recursive_files_count'] - results['root_files_count']
        if extra_files > 0:
            print(f"   Дополнительно найдено: {extra_files} файлов во вложенных папках")

    # 5. Чтение первого найденного файла
    if all_files:
        print("\n5. Чтение первого найденного файла:")
        print_separator("-")
        first_file = all_files[0]
        print(f"   Файл: {first_file}")

        with Timer(f"Чтение файла ({os.path.basename(first_file)})") as timer:
            content = smb.get_one_content(first_file)
        results['file_read_time'] = timer.elapsed_time

        if content:
            file_size_kb = len(content) / 1024
            print(f"\nРезультаты чтения файла:")
            print(f"Размер файла: {len(content)} байт ({file_size_kb:.2f} КБ)")
            print(f"Время чтения: {format_time(results['file_read_time'])}")
            print(f"Скорость: {file_size_kb / results['file_read_time']:.2f} КБ/сек")

            # Показываем первые 200 байт
            print(f"\n   Первые 200 байт содержимого:")
            print(f"   {content[:200]}")
        else:
            print("Не удалось прочитать файл")

    # 6. Тест на чтение нескольких файлов
    if len(all_files) >= 3:
        print("\n6. Чтение нескольких файлов (первые 3):")
        print_separator("-")

        test_files = all_files[:3]
        total_size = 0
        total_time = 0

        for i, file_path in enumerate(test_files, 1):
            file_name = os.path.basename(file_path)
            print(f"\n   {i}. Чтение файла: {file_name}")

            with Timer(f"   Чтение {file_name}") as timer:
                content = smb.get_one_content(file_path)

            if content:
                file_size_kb = len(content) / 1024
                total_size += len(content)
                total_time += timer.elapsed_time
                print(f"      Размер: {file_size_kb:.2f} КБ, Скорость: {file_size_kb / timer.elapsed_time:.2f} КБ/сек")
            else:
                print(f"Не удалось прочитать файл")

        if total_size > 0:
            print(f"\nИтого по {len(test_files)} файлам:")
            print(f"      Общий размер: {total_size / 1024:.2f} КБ")
            print(f"      Общее время: {format_time(total_time)}")
            print(f"      Средняя скорость: {(total_size / 1024) / total_time:.2f} КБ/сек")

    # 7. Итоговый отчет
    print("ИТОГОВЫЙ ОТЧЕТ ПО ПРОИЗВОДИТЕЛЬНОСТИ")

    print(f"\nСводка времени выполнения:")
    print(f"   1. Получение структуры директорий: {format_time(results.get('directory_structure', 0))}")
    print(f"   2. Рекурсивный поиск файлов:      {format_time(results.get('recursive_search_time', 0))}")
    print(f"   3. Поиск в корневой директории:   {format_time(results.get('root_search_time', 0))}")

    if 'file_read_time' in results:
        print(f"   4. Чтение одного файла:           {format_time(results.get('file_read_time', 0))}")

    print(f"\nКоличество найденных файлов:")
    print(f"   - Рекурсивно: {results.get('recursive_files_count', 0)} файлов")
    print(f"   - В корне:    {results.get('root_files_count', 0)} файлов")

    # Вычисляем общее время
    total_time = sum([
        results.get('directory_structure', 0),
        results.get('recursive_search_time', 0),
        results.get('root_search_time', 0),
        results.get('file_read_time', 0)
    ])

    print(f"\nОбщее время выполнения теста: {format_time(total_time)}")
    print(f"Время окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Оценка производительности
    print("\nОценка производительности:")
    if results.get('recursive_search_time', 0) < 1:
        print("Отлично! Поиск файлов выполняется очень быстро (< 1 сек)")
    elif results.get('recursive_search_time', 0) < 5:
        print("Хорошо! Поиск файлов выполняется приемлемо (1-5 сек)")
    elif results.get('recursive_search_time', 0) < 10:
        print("Средняя производительность (5-10 сек)")
    else:
        print("Медленно! Рекомендуется оптимизировать поиск (> 10 сек)")

    print_separator("=")

    return results


def test_smb_performance_with_different_depths():
    """Тест производительности на разной глубине вложенности"""

    smb = SMBFileManager(
        smb_path="smb://127.0.0.1/Share",
        username="username",
        password="password"
    )

    print("ТЕСТ: Производительность на разной глубине вложенности")

    # Тестируем разные настройки рекурсии
    depths = [1, 2, 3, 5, 10]  # Глубина рекурсии
    results = []

    for depth in depths:
        print(f"\nТестирование глубины: {depth}")

        # Здесь нужно создать директории разной глубины или использовать существующие
        # Для демонстрации используем стандартный поиск

        with Timer(f"Поиск с глубиной {depth}") as timer:
            # Модифицируйте метод для ограничения глубины или используйте стандартный
            files = smb.get_files_in_directory(recursive=True)

        results.append({
            'depth': depth,
            'time': timer.elapsed_time,
            'files': len(files)
        })

    # Вывод результатов
    print("\nСравнение производительности:")
    print_separator("-")
    print(f"{'Глубина':<10} {'Время':<15} {'Файлов':<10} {'Скорость':<15}")
    print_separator("-")

    for r in results:
        speed = r['files'] / r['time'] if r['time'] > 0 else 0
        print(f"{r['depth']:<10} {format_time(r['time']):<15} {r['files']:<10} {speed:.2f} файлов/сек")


if __name__ == "__main__":
    # Запускаем основной тест
    test_results = test_smb_recursive_search()

    # тест производительности на разной глубине
    # test_smb_performance_with_different_depths()