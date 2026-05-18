import os
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

            # Использование NetBIOS имен или localhost для клиента
            client_name = 'file_manager_client'

            self.connection = SMBConnection(
                username=self.username,
                password=self.password,
                my_name=client_name,
                remote_name=self.server,
                use_ntlm_v2=True,
                is_direct_tcp=False  # Использовать NetBIOS над TCP
            )

            connected = self.connection.connect(self.server, 139)
            if not connected:
                # Используем прямой TCP на порт 445
                self.connection = SMBConnection(
                    username=self.username,
                    password=self.password,
                    my_name=client_name,
                    remote_name=self.server,
                    use_ntlm_v2=True,
                    is_direct_tcp=True
                )
                connected = self.connection.connect(self.server, 445)

            if connected:
                applogger.debug(f"SMB соединение установлено с {self.server}")
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

    def get_files_in_directory(self, extension: tuple[str] = (".plx", ".xml")) -> list[str]:
        if not self._connect():
            return []

        try:
            # Получение списка файлов и папок
            remote_path = self.remote_path if self.remote_path else ''
            items = self.connection.listPath(self.share, remote_path)

            files = []
            for item in items:
                if item.isDirectory:
                    continue

                filename = item.filename
                if filename not in ['.', '..'] and any(filename.endswith(ext) for ext in extension):
                    # Формирование полного SMB пути
                    full_path = f"smb://{self.server}/{self.share}"
                    if self.remote_path:
                        full_path += f"/{self.remote_path}"
                    full_path += f"/{filename}"
                    files.append(full_path)

            applogger.debug(f"Найдено SMB файлов: {len(files)} в {self.smb_path}")
            if files:
                applogger.debug("Список файлов:")
                applogger.debug("\n".join(f"- {os.path.basename(f)}" for f in files))

            return files

        except Exception as e:
            applogger.error(f"Ошибка при получении списка файлов из SMB: {e}")
            return []
        finally:
            self._disconnect()

    def get_one_content(self, file_path: str) -> bytes:
        if not self._connect():
            return None

        try:
            # Парсинг пути к файлу
            clean_path = file_path
            if clean_path.startswith('smb://'):
                clean_path = clean_path[6:]

            parts = clean_path.split('/')
            if len(parts) < 3:
                applogger.error(f"Некорректный путь к файлу: {file_path}")
                return None

            server = parts[0]
            share = parts[1]
            remote_file_path = '/'.join(parts[2:])

            if server != self.server:
                applogger.error(f"Сервер не соответствует: {server} != {self.server}")
                return None

            # Создание временного файла
            import tempfile

            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                # Скачивание файла через retrieveFile
                with open(temp_path, 'wb') as local_file:
                    self.connection.retrieveFile(self.share, remote_file_path, local_file)

                # Чтение содержимого временного файла
                with open(temp_path, 'rb') as local_file:
                    content = local_file.read()

                applogger.debug(f"Файл успешно прочитан: {remote_file_path}, размер: {len(content)} байт")
                return content

            finally:
                # Удаление временного файла
                os.unlink(temp_path)

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