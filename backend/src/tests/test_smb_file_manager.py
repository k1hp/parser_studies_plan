import sys
import os
from src.services.file_manager import SMBFileManager


def test_smb_connection():

    # Создание экземпляра SMBFileManager
    smb = SMBFileManager(
        "//hostname/Users/UserName/Documents/StudyPlans",
        username="YourUsername",
        password="YourPassword"
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

        # Читаем первый файл
        if files:
            print(f"\nЧтение первого файла: {os.path.basename(files[0])}")
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

    except Exception as e:
        print(f"\nОшибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    test_smb_connection()