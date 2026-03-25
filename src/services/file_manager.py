import os

class FileManager:

    def __init__(self, folder_path: str):
        self.directory = folder_path
        self.file_path = ""


    def get_files_contents(self, file_paths: list[str]) -> list[bytes]:
        contents = []
        for file_path in file_paths:
            try:
                with open(file_path, 'rb') as f:
                    contents.append(f.read())
            except Exception as e:
                print(f"Не удалось прочитать файл {file_path}: {e}")
        return contents

    # Функция для получения всех файлов из папки с указанным расширением (пока что из папки directory на уровне выше)
    def get_files_in_directory(self, extension: tuple[str] = (".plx", ".xml")) -> list[str]:
        if not os.path.exists(self.directory):
            print(f"Ошибка: директории {self.directory} не существует!")
            return []

        if extension is None:
            extensions = ['.xml', '.plx']
        else:
            extensions = [extension]

        files = []
        for f in os.listdir(self.directory):
            if any(f.endswith(ext) for ext in extensions):
                files.append(os.path.join(self.directory, f))

        print(f"Найдено файлов: {len(files)} в директории {self.directory}")
        if files:
            print("Список файлов:")
            for f in files:
                print(f"  - {os.path.basename(f)}")

        return files