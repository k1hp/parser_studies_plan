import os
import io
from src.utils import applogger

try:
    from smb.SMBConnection import SMBConnection
    from smb.base import SharedFile

    SMB_AVAILABLE = True
except ImportError:
    SMB_AVAILABLE = False
    applogger.warning("Библиотека pysmb не установлена. SMB функциональность недоступна.")


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
            return None

    def get_files_in_directory(self, extension: tuple[str] = (".plx", ".xml")) -> list[str]:
        if not os.path.exists(self.directory):
            applogger.error(f"Ошибка: директории {self.directory} не существует!")
            return []

        extensions = [extension]

        files = []
        for f in os.listdir(self.directory):
            if any(f.endswith(ext) for ext in extensions):
                files.append(os.path.join(self.directory, f))

        applogger.debug(f"Найдено файлов: {len(files)} в директории {self.directory}")
        if files:
            applogger.debug("Список файлов:")
            applogger.debug("\n".join(f"- {os.path.basename(f)}" for f in files))

        return files


class SMBFileManager:
    def __init__(self, smb_path: str, username: str = None, password: str = None):
        if not SMB_AVAILABLE:
            raise ImportError("Для работы с SMB необходимо установить библиотеку pysmb: pip install pysmb")

        self.smb_path = smb_path
        self.username = username
        self.password = password
        self.connection = None

        # Парсинг SMB пути
        self.server, self.share, self.remote_path = self._parse_smb_path(smb_path)

    def _parse_smb_path(self, path: str) -> tuple:
        # Очистка пути от лишних слешей
        path = path.replace('\\', '/')

        # Удаление протокола если есть
        if path.startswith('smb://'):
            path = path[6:]
        elif path.startswith('//'):
            path = path[2:]

        parts = path.split('/')

        if len(parts) < 2:
            raise ValueError(f"Некорректный SMB путь: {self.smb_path}. Ожидается формат //server/share/folder")

        server = parts[0]
        share = parts[1]
        remote_path = '/'.join(parts[2:]) if len(parts) > 2 else ''

        return server, share, remote_path

    def _connect(self):
        try:
            from smb.SMBConnection import SMBConnection

            client_name = 'file_manager_client'

            # Сначала пробуем подключение через прямой TCP (порт 445) - SMB3
            applogger.debug(f"Попытка подключения к {self.server} через порт 445 (SMB3)")

            self.connection = SMBConnection(
                username=self.username,
                password=self.password,
                my_name=client_name,
                remote_name=self.server,
                use_ntlm_v2=True,
                is_direct_tcp=True  # Используем прямой TCP для SMB3
            )

            connected = self.connection.connect(self.server, 445)

            if connected:
                applogger.debug(f"SMB соединение установлено с {self.server} через порт 445")
                return True
            else:
                # Если не получилось через 445, пробуем через NetBIOS (порт 139) - SMB1/2
                applogger.debug(f"Попытка подключения к {self.server} через порт 139 (NetBIOS)")
                self.connection = SMBConnection(
                    username=self.username,
                    password=self.password,
                    my_name=client_name,
                    remote_name=self.server,
                    use_ntlm_v2=True,
                    is_direct_tcp=False
                )
                connected = self.connection.connect(self.server, 139)

                if connected:
                    applogger.debug(f"SMB соединение установлено с {self.server} через порт 139")
                    return True
                else:
                    applogger.error(f"Не удалось подключиться к {self.server}")
                    self.connection = None
                    return False

        except Exception as e:
            applogger.error(f"Ошибка SMB подключения: {e}")
            self.connection = None
            return False

    def _disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def _get_files_recursive(self, current_path: str, extension: tuple, files_list: list, base_path: str = ""):
        try:
            # Получаем список элементов в текущей директории
            items = self.connection.listPath(self.share, current_path)

            for item in items:
                if item.filename in ['.', '..']:
                    continue

                # Формируем полный путь к элементу
                if current_path:
                    item_path = f"{current_path}/{item.filename}"
                else:
                    item_path = item.filename

                if item.isDirectory:
                    # Если это директория, рекурсивно обходим её
                    applogger.debug(f"Обработка директории: {item_path}")
                    self._get_files_recursive(item_path, extension, files_list, base_path)
                else:
                    # Если это файл, проверяем расширение
                    if any(item.filename.lower().endswith(ext.lower()) for ext in extension):
                        # Формируем полный SMB путь к файлу
                        full_path = f"smb://{self.server}/{self.share}"
                        if item_path:
                            full_path += f"/{item_path}"
                        files_list.append(full_path)
                        applogger.debug(f"Найден файл: {item_path}")

        except Exception as e:
            applogger.error(f"Ошибка при обходе директории {current_path}: {e}")

    def get_files_in_directory(self, extension: tuple[str] = (".plx", ".xml"), recursive: bool = True) -> list[str]:
        if not self._connect():
            return []

        try:
            files = []

            if recursive:
                # Рекурсивный поиск во всех вложенных папках
                remote_path = self.remote_path if self.remote_path else ''
                applogger.debug(f"Рекурсивный поиск файлов в: {self.share}/{remote_path}")
                self._get_files_recursive(remote_path, extension, files)
            else:
                # Поиск только в текущей директории (без рекурсии)
                remote_path = self.remote_path if self.remote_path else ''
                items = self.connection.listPath(self.share, remote_path)

                for item in items:
                    if item.isDirectory or item.filename in ['.', '..']:
                        continue

                    filename = item.filename
                    if any(filename.endswith(ext) for ext in extension):
                        full_path = f"smb://{self.server}/{self.share}"
                        if self.remote_path:
                            full_path += f"/{self.remote_path}"
                        full_path += f"/{filename}"
                        files.append(full_path)

            applogger.debug(f"Найдено SMB файлов: {len(files)} в {self.smb_path}")

            # Выводим структуру найденных файлов
            if files:
                applogger.debug("Список найденных файлов:")
                for f in files[:10]:  # Показываем первые 10 для отладки
                    applogger.debug(f"- {f}")
                if len(files) > 10:
                    applogger.debug(f"... и еще {len(files) - 10} файлов")
            else:
                applogger.warning(f"Файлы с расширениями {extension} не найдены в {self.smb_path}")

            return files

        except Exception as e:
            applogger.error(f"Ошибка при получении списка файлов из SMB: {e}")
            return []
        finally:
            self._disconnect()

    def get_file_stream(self, file_path: str, chunk_size: int = 8192):
        if not self._connect():
            return None

        try:
            # Парсинг пути к файлу
            if file_path.startswith("smb://"):
                file_path = file_path[6:]

            parts = file_path.split("/")
            if len(parts) < 3:
                applogger.error(f"Некорректный путь к файлу: {file_path}")
                return None

            server = parts[0]
            share = parts[1]
            remote_file_path = "/".join(parts[2:])

            if server != self.server:
                applogger.error(f"Сервер не соответствует: {server} != {self.server}")
                return None

            # Создаем BytesIO объект для потокового чтения
            file_obj = io.BytesIO()

            # Скачиваем файл в BytesIO объект
            applogger.debug(f"Чтение файла: {share}/{remote_file_path}")
            self.connection.retrieveFile(share, remote_file_path, file_obj)

            # Перемещаем указатель в начало
            file_obj.seek(0)

            def file_generator():
                try:
                    while True:
                        chunk = file_obj.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
                finally:
                    file_obj.close()
                    self._disconnect()

            return file_generator()

        except Exception as e:
            applogger.error(f"Ошибка при открытии SMB файла {file_path}: {e}")
            self._disconnect()
            return None

    def read_file_chunked(self, file_path: str, callback, chunk_size: int = 8192):
        stream = self.get_file_stream(file_path, chunk_size)
        if stream is None:
            return False

        try:
            for chunk in stream:
                callback(chunk)
            return True
        except Exception as e:
            applogger.error(f"Ошибка при чтении файла {file_path}: {e}")
            return False

    def get_one_content(self, file_path: str) -> bytes:
        if not self._connect():
            return None

        try:
            if file_path.startswith("smb://"):
                file_path = file_path[6:]

            parts = file_path.split("/")
            if len(parts) < 3:
                applogger.error(f"Некорректный путь к файлу: {file_path}")
                return None

            server = parts[0]
            share = parts[1]
            remote_file_path = "/".join(parts[2:])

            if server != self.server:
                applogger.error(f"Сервер не соответствует: {server} != {self.server}")
                return None

            # Используем BytesIO для чтения файла
            file_obj = io.BytesIO()
            self.connection.retrieveFile(share, remote_file_path, file_obj)

            # Получаем содержимое
            file_obj.seek(0)
            content = file_obj.read()
            file_obj.close()

            applogger.debug(f"Файл успешно прочитан: {remote_file_path} (размер: {len(content)} байт)")
            return content

        except Exception as e:
            applogger.error(f"Ошибка при чтении SMB файла {file_path}: {e}")
            return None
        finally:
            self._disconnect()

    def get_files_contents(self, file_paths: list[str]) -> list[bytes]:
        contents = []
        for file_path in file_paths:
            content = self.get_one_content(file_path)
            if content is not None:
                contents.append(content)
        return contents

    def process_files_streaming(self, file_paths: list[str], process_callback, chunk_size: int = 8192):
        results = []
        for file_path in file_paths:
            stream = self.get_file_stream(file_path, chunk_size)
            if stream:
                try:
                    result = process_callback(stream, file_path)
                    results.append(result)
                except Exception as e:
                    applogger.error(f"Ошибка при обработке файла {file_path}: {e}")
                    results.append(None)
        return results

    def get_directory_structure(self, current_path: str = "", indent: int = 0):
        """
        Вспомогательный метод для отладки - выводит структуру директорий.
        """
        if not self._connect():
            return

        try:
            remote_path = current_path if current_path else (self.remote_path if self.remote_path else '')
            items = self.connection.listPath(self.share, remote_path)

            for item in items:
                if item.filename in ['.', '..']:
                    continue

                prefix = "  " * indent
                if item.isDirectory:
                    applogger.debug(f"{prefix} {item.filename}/")
                    # Рекурсивно показываем содержимое директории
                    new_path = f"{remote_path}/{item.filename}" if remote_path else item.filename
                    self.get_directory_structure(new_path, indent + 1)
                else:
                    applogger.debug(f"{prefix} {item.filename}")

        except Exception as e:
            applogger.error(f"Ошибка при получении структуры директории: {e}")
        finally:
            if indent == 0:
                self._disconnect()