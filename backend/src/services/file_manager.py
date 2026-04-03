from pathlib import Path
from src.utils import applogger

class FileManager:

    def __init__(self, folder_path: str):
        self.directory = folder_path

    def get_files_contents(self, file_paths: list[str]) -> list[bytes]:
        contents = []
        for file_path in file_paths:
            contents.append(self.get_one_content(file_path))
        return contents

    def get_one_content(self, file_path: str) -> bytes:
        try:
            with open(file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            applogger.error(f"Не удалось прочитать файл {file_path}: {e}")

    def get_files_in_directory(self, extension: tuple[str, ...] = (".plx", ".xml")) -> list[Path]:
        directory = Path(self.directory)

        if not directory.exists():
            applogger.error(f"Ошибка: директории {self.directory} не существует!")
            return []

        extensions = [extension]

        files = [
            f for f in directory.iterdir()
            if f.is_file() and f.suffix in extensions
        ]

        applogger.debug(f"Найдено файлов: {len(files)} в директории {self.directory}")
        if files:
            applogger.debug("Список файлов:")
            applogger.debug("\n".join(f"- {f.name}" for f in files))

        return files