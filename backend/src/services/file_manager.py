import os
import io
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
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

        self.server, self.share, self.remote_path = self._parse_smb_path(smb_path)

    @property
    def is_connected(self) -> bool:
        return self.connection is not None

    def connect(self) -> bool:
        if self.is_connected:
            applogger.debug("SMB соединение уже активно, переиспользуем")
            return True
        return self._connect()

    def disconnect(self):
        self._disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False

    def _parse_smb_path(self, path: str) -> tuple:
        path = path.replace('\\', '/')

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

            applogger.debug(f"Попытка подключения к {self.server} через порт 445 (SMB3)")

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
                applogger.debug(f"SMB соединение установлено с {self.server} через порт 445")
                return True
            else:
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

    def _ensure_connection(self):
        if not self.is_connected:
            applogger.debug("Авто-подключение к SMB...")
            self.connect()

    def _make_worker_connection(self):
        from smb.SMBConnection import SMBConnection

        conn = SMBConnection(
            username=self.username,
            password=self.password,
            my_name='file_manager_worker',
            remote_name=self.server,
            use_ntlm_v2=True,
            is_direct_tcp=True
        )
        if conn.connect(self.server, 445):
            return conn

        conn = SMBConnection(
            username=self.username,
            password=self.password,
            my_name='file_manager_worker',
            remote_name=self.server,
            use_ntlm_v2=True,
            is_direct_tcp=False
        )
        if conn.connect(self.server, 139):
            return conn
        return None

    def _scan_single_dir(self, conn, dir_path: str, extension: tuple):
        files = []
        subdirs = []
        items = conn.listPath(self.share, dir_path)
        for item in items:
            if item.filename in ['.', '..']:
                continue
            item_path = f"{dir_path}/{item.filename}" if dir_path else item.filename
            if item.isDirectory:
                subdirs.append(item_path)
            elif any(item.filename.lower().endswith(ext.lower()) for ext in extension):
                full_path = f"smb://{self.server}/{self.share}/{item_path}"
                files.append(full_path)
        return files, subdirs

    def get_files_in_directory(self, extension: tuple[str] = (".plx", ".xml"),
                                recursive: bool = True, max_workers: int = 8) -> list[str]:
        if not recursive:
            return self._get_files_flat(extension)

        self._ensure_connection()
        return self._get_files_parallel(extension, max_workers)

    def _get_files_flat(self, extension: tuple[str]) -> list[str]:
        self._ensure_connection()

        try:
            remote_path = self.remote_path if self.remote_path else ''
            items = self.connection.listPath(self.share, remote_path)
            files = []

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
            return files

        except Exception as e:
            applogger.error(f"Ошибка при получении списка файлов из SMB: {e}")
            return []

    def _get_files_sequential(self, extension: tuple[str]) -> list[str]:
        """Исходный рекурсивный обход — последовательный, для сравнения."""
        self._ensure_connection()

        files = []

        def _recurse(current_path: str):
            try:
                items = self.connection.listPath(self.share, current_path)
                for item in items:
                    if item.filename in ['.', '..']:
                        continue
                    item_path = f"{current_path}/{item.filename}" if current_path else item.filename
                    if item.isDirectory:
                        _recurse(item_path)
                    elif any(item.filename.lower().endswith(ext.lower()) for ext in extension):
                        full_path = f"smb://{self.server}/{self.share}/{item_path}"
                        files.append(full_path)
            except Exception as e:
                applogger.error(f"Ошибка при обходе {current_path}: {e}")

        remote_path = self.remote_path if self.remote_path else ''
        _recurse(remote_path)

        applogger.debug(f"Найдено SMB файлов (последовательно): {len(files)} в {self.smb_path}")
        return files

    def _get_files_parallel(self, extension: tuple[str], max_workers: int = 8) -> list[str]:
        """Параллельный рекурсивный обход: каждый listPath в своём потоке."""
        applogger.debug(f"Параллельный обход (workers={max_workers}): {self.share}/{self.remote_path}")

        all_files = []
        files_lock = threading.Lock()

        # Счётчик оставшихся директорий для сканирования
        remaining = 1  # корневая директория
        remaining_lock = threading.Lock()
        remaining_cond = threading.Condition(remaining_lock)

        dir_queue = []
        queue_lock = threading.Lock()
        stopped = threading.Event()

        root = self.remote_path if self.remote_path else ''
        dir_queue.append(root)

        def worker():
            nonlocal remaining
            conn = self._make_worker_connection()
            if conn is None:
                with remaining_lock:
                    remaining -= 1
                    if remaining == 0:
                        remaining_cond.notify_all()
                return

            try:
                while not stopped.is_set():
                    # Получить следующую директорию
                    with queue_lock:
                        if dir_queue:
                            dir_path = dir_queue.pop()
                        else:
                            dir_path = None

                    if dir_path is None:
                        # Нет директорий — ждём появления новых или завершения
                        with remaining_lock:
                            if remaining == 0:
                                break
                        # Короткая пауза перед повторной проверкой
                        stopped.wait(0.1)
                        continue

                    try:
                        files, subdirs = self._scan_single_dir(conn, dir_path, extension)

                        if subdirs:
                            with queue_lock:
                                dir_queue.extend(subdirs)
                            with remaining_lock:
                                remaining += len(subdirs)
                                remaining_cond.notify_all()

                        if files:
                            with files_lock:
                                all_files.extend(files)

                    except Exception as e:
                        applogger.error(f"Ошибка при сканировании {dir_path}: {e}")
                    finally:
                        with remaining_lock:
                            remaining -= 1
                            if remaining == 0:
                                remaining_cond.notify_all()

            finally:
                conn.close()

        # Запуск воркеров
        workers = []
        for _ in range(max_workers):
            t = threading.Thread(target=worker, daemon=True)
            t.start()
            workers.append(t)

        # Ждём завершения
        with remaining_lock:
            while remaining > 0:
                remaining_cond.wait()

        stopped.set()

        for t in workers:
            t.join(timeout=5)

        applogger.debug(f"Найдено SMB файлов (параллельно): {len(all_files)} в {self.smb_path}")
        if all_files:
            applogger.debug(f"Примеры: {[f.rsplit('/', 1)[-1] for f in all_files[:5]]}")

        return all_files

    def get_directory_structure(self):
        self._ensure_connection()

        def _traverse(path: str, depth: int = 0, max_depth: int = 10):
            if depth > max_depth:
                return {}

            result = {}
            try:
                items = self.connection.listPath(self.share, path)
                for item in items:
                    if item.filename in ['.', '..']:
                        continue
                    item_path = f"{path}/{item.filename}" if path else item.filename
                    if item.isDirectory:
                        result[item.filename + '/'] = _traverse(item_path, depth + 1, max_depth)
                    else:
                        result[item.filename] = None
            except Exception as e:
                applogger.error(f"Ошибка при обходе {path}: {e}")
            return result

        remote_path = self.remote_path if self.remote_path else ''
        return {self.share + '/': _traverse(remote_path)}

    def print_directory_structure(self, structure: dict = None, indent: str = ""):
        if structure is None:
            structure = self.get_directory_structure()

        for name, children in sorted(structure.items()):
            if children is None:
                print(f"{indent}  {name}")
            else:
                print(f"{indent}  {name}")
                self.print_directory_structure(children, indent + "    ")

    def get_file_stream(self, file_path: str, chunk_size: int = 8192):
        self._ensure_connection()

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

            file_obj = io.BytesIO()
            applogger.debug(f"Чтение файла: {share}/{remote_file_path}")
            self.connection.retrieveFile(share, remote_file_path, file_obj)

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

            return file_generator()

        except Exception as e:
            applogger.error(f"Ошибка при открытии SMB файла {file_path}: {e}")
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
        self._ensure_connection()

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

            file_obj = io.BytesIO()
            self.connection.retrieveFile(share, remote_file_path, file_obj)

            file_obj.seek(0)
            content = file_obj.read()
            file_obj.close()

            applogger.debug(f"Файл успешно прочитан: {remote_file_path} (размер: {len(content)} байт)")
            return content

        except Exception as e:
            applogger.error(f"Ошибка при чтении SMB файла {file_path}: {e}")
            return None

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
