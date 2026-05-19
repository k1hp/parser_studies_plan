import sys
import os
from src.services.file_manager import SMBFileManager


def test_smb_connection():
    # Создание экземпляра SMBFileManager
    smb = SMBFileManager(
        "smb://hostname_or_ip/Share",
        username="username",
        password="password"
    )

    print(f"Подключение к SMB шаре...")
    print(f"Путь: {smb.smb_path}")

    try:
        # Получаем список файлов
        print("\nПоиск файлов .plx и .xml...")
        files = smb.get_files_in_directory()

        if not files:
            print("Файлы не найдены!")
            return

        print(f"\nНайдено файлов: {len(files)}")
        print("\nСписок найденных файлов:")
        for i, f in enumerate(files, 1):
            print(f"  {i}. {os.path.basename(f)}")

        # Читаем первый файл (старый способ)
        if files:
            print(f"\n--- Тест 1: Чтение через get_one_content() ---")
            print(f"Чтение первого файла: {os.path.basename(files[0])}")
            content = smb.get_one_content(files[0])

            if content is None:
                print("Не удалось прочитать файл")
                return

            print(f"\nФайл успешно прочитан!")
            print(f"   Размер: {len(content)} байт")

            # Показываем первые 200 байт
            print(f"\n   Первые 200 байт содержимого:")
            try:
                # Пробуем декодировать как UTF-16
                text_content = content[:200].decode('utf-16', errors='ignore')
                print(text_content)
            except:
                print(content[:200])

        # Тест потокового чтения
        if files:
            print(f"\n--- Тест 2: Потоковое чтение через read_file_chunked() ---")
            print(f"Чтение второго файла (если есть): {os.path.basename(files[1]) if len(files) > 1 else files[0]}")

            def process_chunk(chunk):
                print(f"  Получен чанк размером {len(chunk)} байт")

            success = smb.read_file_chunked(files[1] if len(files) > 1 else files[0], process_chunk, chunk_size=4096)
            if success:
                print("Потоковое чтение завершено успешно!")
            else:
                print("Ошибка при потоковом чтении")

        # Тест потоковой обработки
        if len(files) >= 2:
            print(f"\n--- Тест 3: Потоковая обработка через process_files_streaming() ---")

            def process_file(file_stream, file_path):
                total_size = 0
                chunk_count = 0
                for chunk in file_stream:
                    total_size += len(chunk)
                    chunk_count += 1
                return {"path": file_path, "size": total_size, "chunks": chunk_count}

            results = smb.process_files_streaming(files[:2], process_file, chunk_size=4096)
            for result in results:
                if result:
                    print(f"Файл {os.path.basename(result['path'])}: {result['size']} байт, {result['chunks']} чанков")

    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_smb_connection()