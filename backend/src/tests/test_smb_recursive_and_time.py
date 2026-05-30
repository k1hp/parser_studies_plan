# test_smb_recursive_and_time.py
import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.config import SMB_PATH, SMB_USERNAME, SMB_PASSWORD
from src.services.file_manager import SMBFileManager


class Timer:
    def __init__(self, name: str = "Операция"):
        self.name = name
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        print(f"\n>>> {self.name}...")
        return self

    def __exit__(self, *args):
        self.end_time = time.perf_counter()
        elapsed = self.elapsed_time
        print(f"<<< {self.name}")
        print(f"    Время: {format_time(elapsed)}")

    @property
    def elapsed_time(self):
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0


def print_separator(char="=", length=60):
    print(char * length)


def format_time(seconds: float) -> str:
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


def test_sequential_vs_parallel():
    """Сравнение последовательного vs параллельного сканирования"""

    smb = SMBFileManager(
        SMB_PATH,
        username=SMB_USERNAME,
        password=SMB_PASSWORD
    )

    print_separator("=")
    print("ТЕСТ: Последовательное vs Параллельное сканирование SMB")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("=")

    # --- Подключение ---
    print("\n1. Подключение к SMB:")
    print_separator("-")
    with Timer("Подключение") as timer:
        connected = smb.connect()
    if not connected:
        print("   Нет соединения. Тест остановлен.")
        return
    print(f"   Статус: подключено ({smb.server}/{smb.share})")

    # --- Последовательное сканирование ---
    print("\n2. Последовательный обход (один listPath за раз):")
    print_separator("-")
    with Timer("Последовательное сканирование") as timer:
        files_seq = smb._get_files_sequential((".plx", ".xml"))
    seq_time = timer.elapsed_time
    seq_count = len(files_seq)
    print(f"   Файлов: {seq_count}")

    # --- Параллельное сканирование с разным числом воркеров ---
    worker_counts = [2, 4, 8, 16]
    parallel_results = {}

    print("\n3. Параллельный обход (listPath в отдельных потоках):")
    print_separator("-")

    for workers in worker_counts:
        with Timer(f"Параллельно, workers={workers}") as timer:
            files_par = smb._get_files_parallel((".plx", ".xml"), max_workers=workers)
        parallel_results[workers] = {
            'time': timer.elapsed_time,
            'count': len(files_par),
        }
        print(f"   Файлов: {len(files_par)}")

        # Проверка что результаты совпадают
        if set(files_par) == set(files_seq):
            print(f"   Совпадение с sequential: OK")
        else:
            only_seq = set(files_seq) - set(files_par)
            only_par = set(files_par) - set(files_seq)
            if only_seq:
                print(f"   Только в sequential: {len(only_seq)}")
            if only_par:
                print(f"   Только в parallel:  {len(only_par)}")

    # --- Сводка ---
    print("\n4. Сводка производительности:")
    print_separator("-")
    print(f"\n   {'Метод':<30} {'Время':<20} {'Файлов':<10} {'Ускорение':<15}")
    print(f"   {'-'*30} {'-'*20} {'-'*10} {'-'*15}")
    print(f"   {'Последовательный':<30} {format_time(seq_time):<20} {seq_count:<10} {'1.0x (база)':<15}")

    best_time = seq_time
    best_workers = 1
    for workers in worker_counts:
        r = parallel_results[workers]
        speedup = seq_time / r['time'] if r['time'] > 0 else float('inf')
        marker = " <-- лучшее!" if r['time'] < best_time else ""
        print(f"   {f'Параллельный ({workers} пот.)':<30} {format_time(r['time']):<20} {r['count']:<10} {f'{speedup:.1f}x':<15}{marker}")
        if r['time'] < best_time:
            best_time = r['time']
            best_workers = workers

    saved = seq_time - best_time
    print(f"\n   Лучший результат: {best_workers} потоков")
    print(f"   Сэкономлено: {format_time(saved)} ({seq_time / best_time:.1f}x ускорение)")

    # --- Чтение файлов ---
    print("\n5. Чтение первых 3 файлов (проверка что сессия жива):")
    print_separator("-")
    test_files = files_seq[:3]
    total_size = 0
    total_time = 0

    for i, fp in enumerate(test_files, 1):
        name = fp.rsplit('/', 1)[-1] if '/' in fp else fp
        with Timer(f"Чтение {name}") as timer:
            content = smb.get_one_content(fp)
        if content:
            kb = len(content) / 1024
            total_size += len(content)
            total_time += timer.elapsed_time
            print(f"   {i}. {name}: {kb:.1f} КБ за {format_time(timer.elapsed_time)}")

    if total_size > 0:
        print(f"\n   Общий объём: {total_size / 1024:.1f} КБ")
        print(f"   Общее время чтения: {format_time(total_time)}")
        print(f"   Средняя скорость: {(total_size / 1024) / max(total_time, 0.001):.0f} КБ/сек")

    # --- Отключение ---
    print("\n6. Отключение:")
    print_separator("-")
    smb.disconnect()
    print(f"   is_connected: {smb.is_connected}")

    # --- Итог ---
    print("\n")
    print_separator("=")
    print("ИТОГ")
    print_separator("=")
    print(f"   Последовательно: {format_time(seq_time)}")
    print(f"   Параллельно (лучший): {format_time(best_time)} ({best_workers} потоков)")
    print(f"   Ускорение: x{seq_time / max(best_time, 0.001):.1f}")
    print(f"   Время окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("=")


def test_parallel_only():
    """Быстрый тест — только параллельное сканирование (без долгого sequential)"""

    smb = SMBFileManager(
        SMB_PATH,
        username=SMB_USERNAME,
        password=SMB_PASSWORD
    )

    print_separator("=")
    print("ТЕСТ: Параллельное сканирование (без sequential для быстроты)")
    print(f"Время начала: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print_separator("=")

    smb.connect()
    print(f"   Подключено: {smb.is_connected}")

    with Timer("Параллельное сканирование (8 workers)") as timer:
        files = smb.get_files_in_directory(recursive=True, max_workers=8)

    print(f"\n   Найдено файлов: {len(files)}")
    print(f"   Время: {format_time(timer.elapsed_time)}")

    if files:
        print(f"\n   Первые 10 файлов:")
        for i, f in enumerate(files[:10], 1):
            print(f"   {i}. {f.rsplit('/', 1)[-1] if '/' in f else f}")

    smb.disconnect()
    print(f"\n   Отключено. Время окончания: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    import sys
    if "--fast" in sys.argv:
        test_parallel_only()
    else:
        test_sequential_vs_parallel()
