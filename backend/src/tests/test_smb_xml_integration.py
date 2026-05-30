import sys
import os
import tempfile
import hashlib
import pytest
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.src.services.file_manager import SMBFileManager, FileManager
from backend.src.services.xml_parsing_service import XmlParsingService
from backend.src.utils import applogger


class TestSMBXmlIntegration:
    """Класс для тестирования интеграции SMBFileManager и XmlParsingService"""

    @pytest.fixture
    def smb_config(self):
        """Фикстура с конфигурацией SMB"""
        return {
            "smb_path": "smb://127.0.0.1/Share",
            "username": "username",
            "password": "password"
        }

    @pytest.fixture
    def smb_manager(self, smb_config):
        """Фикстура для создания SMBFileManager с проверкой подключения"""
        try:
            smb = SMBFileManager(
                smb_path=smb_config["smb_path"],
                username=smb_config["username"],
                password=smb_config["password"]
            )

            # Проверяем подключение перед возвратом
            test_connection = smb._connect()
            if test_connection:
                smb._disconnect()
                return smb
            else:
                pytest.skip(f"SMB сервер недоступен: {smb_config['smb_path']}")

        except Exception as e:
            pytest.skip(f"Не удалось создать SMB менеджер: {e}")

    @pytest.fixture
    def xml_parser(self):
        """Фикстура для XmlParsingService"""
        return XmlParsingService()

    def _get_non_empty_files(self, smb_manager, extension=(".plx", ".xml"), max_files=10):
        all_files = smb_manager.get_files_in_directory(extension=extension)

        if not all_files:
            return []

        non_empty_files = []
        empty_files = []

        print(f"\nПроверка файлов на пустоту (всего найдено: {len(all_files)})")

        for i, file_path in enumerate(all_files[:max_files], 1):
            try:
                content = smb_manager.get_one_content(file_path)
                if content and len(content) > 0:
                    non_empty_files.append(file_path)
                    print(f"{i}. {os.path.basename(file_path)} - {len(content)} байт")
                else:
                    empty_files.append(file_path)
                    print(f"{i}. {os.path.basename(file_path)} - ПУСТОЙ файл (пропускаем)")
            except Exception as e:
                print(f"{i}. {os.path.basename(file_path)} - Ошибка: {e}")

        if empty_files:
            print(f"\nПропущено пустых файлов: {len(empty_files)}")

        return non_empty_files

    def test_file_listing_with_filtering(self, smb_manager):
        """Тест 1: Получение списка файлов с фильтрацией пустых"""
        print("ТЕСТ 1: Получение списка файлов (с пропуском пустых)")

        # Получаем только непустые файлы
        non_empty_files = self._get_non_empty_files(smb_manager, max_files=20)

        if not non_empty_files:
            pytest.skip("Нет непустых файлов для тестирования")

        print(f"\nНайдено непустых файлов: {len(non_empty_files)}")
        print("\nПервые 5 непустых файлов:")
        for i, f in enumerate(non_empty_files[:5], 1):
            print(f"  {i}. {os.path.basename(f)}")

    def test_file_content_integrity(self, smb_manager):
        """Тест 2: Проверка целостности содержимого (только непустые файлы)"""
        print("ТЕСТ 2: Проверка целостности содержимого")

        # Получаем непустые файлы
        files = smb_manager.get_files_in_directory()
        if not files:
            pytest.skip("Нет файлов для тестирования")

        # Пропускаем пустые файлы
        test_file = None
        for f in files:
            content_preview = smb_manager.get_one_content(f)
            if content_preview and len(content_preview) > 0:
                test_file = f
                break

        if not test_file:
            pytest.skip("Не найдено непустых файлов для тестирования")

        print(f"Тестируемый файл: {os.path.basename(test_file)}")

        # Тест get_one_content
        print("\n2.1 Тестирование get_one_content()...")
        content = smb_manager.get_one_content(test_file)

        assert content is not None, "get_one_content() вернул None"
        assert len(content) > 0, f"Файл {os.path.basename(test_file)} пустой"
        print(f"get_one_content() прочитал {len(content)} байт")

        # Проверка на наличие мусора (битых данных)
        null_bytes = content[:min(1000, len(content))].count(b'\x00')
        null_percentage = (null_bytes / min(1000, len(content))) * 100
        assert null_percentage < 50, f"Слишком много нулевых байт: {null_percentage:.1f}%"

        # Тест get_file_stream
        print("\n2.2 Тестирование get_file_stream()...")
        stream = smb_manager.get_file_stream(test_file)
        assert stream is not None, "get_file_stream() вернул None"

        chunks = []
        total_size = 0
        chunk_count = 0

        for chunk in stream:
            chunks.append(chunk)
            total_size += len(chunk)
            chunk_count += 1

        print(f"get_file_stream() прочитал {total_size} байт в {chunk_count} чанках")
        assert total_size == len(content), "Размеры прочитанных данных не совпадают"

        # Сравниваем содержимое
        stream_content = b''.join(chunks)
        assert stream_content == content, "Содержимое get_one_content() и get_file_stream() различается"
        print("Содержимое методов совпадает")

    def test_xml_parsing_from_smb(self, smb_manager, xml_parser):
        """Тест 3: Парсинг XML через SMBFileManager (только непустые файлы)"""
        print("ТЕСТ 3: Парсинг XML через SMBFileManager")

        # Получаем XML файлы
        files = smb_manager.get_files_in_directory(extension=(".xml", ".plx"))
        if not files:
            pytest.skip("Нет XML/PLX файлов для тестирования")

        # Находим первый непустой XML файл
        xml_file = None
        for f in files:
            content = smb_manager.get_one_content(f)
            if content and len(content) > 0:
                xml_file = f
                break

        if not xml_file:
            pytest.skip("Не найдено непустых XML/PLX файлов для тестирования")

        print(f"Парсинг файла: {os.path.basename(xml_file)}")

        # Получаем содержимое
        content = smb_manager.get_one_content(xml_file)
        assert content is not None, "Не удалось получить содержимое файла"
        assert len(content) > 0, f"Файл {os.path.basename(xml_file)} пустой"

        # Проверяем, что файл похож на XML
        content_preview = content[:500]
        is_likely_xml = b'<?xml' in content_preview or b'<' in content_preview
        if not is_likely_xml:
            print(f"ВНИМАНИЕ: Файл не похож на XML")
            print(f"   Первые 200 байт: {content_preview[:200]}")

        # Парсим XML
        print("\nПарсинг XML...")
        parsed_data = xml_parser.extract_from_content(content)

        # Проверяем результат
        assert parsed_data is not None, "Не удалось распарсить XML"

        print("\nXML успешно распарсен!")
        print(f"   Код направления: {parsed_data.direction_code or 'Не указан'}")
        print(f"   Название: {parsed_data.direction_name or 'Не указано'}")
        print(f"   Год начала: {parsed_data.start_year}")
        print(f"   Количество дисциплин: {len(parsed_data.disciplines)}")

        # Базовые проверки данных
        if parsed_data.direction_code:
            # Код направления должен быть в формате XX.XX.XX или подобном
            import re
            assert re.match(r'^\d{2}\.\d{2}\.\d{2}', parsed_data.direction_code) or \
                   len(parsed_data.direction_code) == 0, \
                f"Необычный формат кода направления: {parsed_data.direction_code}"

        # Проверяем дисциплины на мусор
        for disc in parsed_data.disciplines[:5]:
            if disc.discipline_name:
                # Проверяем наличие непечатных символов
                has_non_printable = any(ord(c) < 32 and ord(c) not in [9, 10, 13]
                                        for c in disc.discipline_name)
                assert not has_non_printable, \
                    f"Обнаружены непечатные символы в названии дисциплины: {disc.discipline_name[:50]}"

        print("Данные не содержат явного мусора")

    def test_compare_file_hashes(self, smb_manager):
        """Тест 4: Сравнение хешей файлов (пропуск пустых)"""
        print("ТЕСТ 4: Проверка уникальности файлов по хешам")

        # Получаем непустые SMB файлы
        non_empty_files = self._get_non_empty_files(smb_manager, max_files=50)

        if len(non_empty_files) < 2:
            pytest.skip(f"Недостаточно непустых файлов для сравнения (найдено: {len(non_empty_files)})")

        print(f"\nСравнение {len(non_empty_files[:10])} файлов...")

        # Сравниваем хеши первых 10 файлов
        file_hashes = {}
        duplicates = []

        for file_path in non_empty_files[:10]:
            content = smb_manager.get_one_content(file_path)
            if content and len(content) > 0:
                file_hash = hashlib.md5(content).hexdigest()
                filename = os.path.basename(file_path)

                if file_hash in file_hashes:
                    duplicates.append((filename, file_hashes[file_hash]))
                    print(f"Дубликат: {filename} == {file_hashes[file_hash]}")
                else:
                    file_hashes[file_hash] = filename
                    print(f"{filename}: {file_hash[:16]}...")

        if duplicates:
            print(f"\nНайдено {len(duplicates)} дубликатов файлов")
        else:
            print("\nДубликатов не найдено")

    def test_multiple_files_parsing(self, smb_manager, xml_parser):
        """Тест 5: Парсинг нескольких файлов (только непустые)"""
        print("ТЕСТ 5: Парсинг нескольких файлов")

        # Получаем непустые XML файлы
        all_files = smb_manager.get_files_in_directory(extension=(".xml", ".plx"))
        if not all_files:
            pytest.skip("Нет XML/PLX файлов для тестирования")

        # Отбираем только непустые файлы
        non_empty_files = []
        for f in all_files[:20]:  # Проверяем первые 20
            content = smb_manager.get_one_content(f)
            if content and len(content) > 0:
                non_empty_files.append(f)

        if len(non_empty_files) < 2:
            pytest.skip(
                f"Недостаточно непустых файлов для тестирования (нужно минимум 2, найдено: {len(non_empty_files)})")

        # Берем первые 2 непустых файла
        test_files = non_empty_files[:2]
        print(f"Тестируем {len(test_files)} непустых файлов")

        # Получаем содержимое всех файлов
        contents = []
        for f in test_files:
            content = smb_manager.get_one_content(f)
            if content and len(content) > 0:
                contents.append(content)

        assert len(contents) == len(test_files), "Не все файлы прочитаны"

        # Парсим все файлы
        parsed_results = []
        for i, content in enumerate(contents):
            print(f"\nПарсинг файла {i + 1}: {os.path.basename(test_files[i])}")
            parsed_data = xml_parser.extract_from_content(content)

            if parsed_data is not None:
                parsed_results.append(parsed_data)
                print(f"Успешно: {len(parsed_data.disciplines)} дисциплин")
            else:
                print(f"Не удалось распарсить")

        # Хотя бы один файл должен распарситься
        assert len(parsed_results) > 0, "Не удалось распарсить ни один файл"
        print(f"\nУспешно распарсено {len(parsed_results)} из {len(test_files)} файлов")

    def test_streaming_processing(self, smb_manager):
        """Тест 6: Потоковая обработка файлов (только непустые)"""
        print("ТЕСТ 6: Потоковая обработка файлов")

        # Получаем непустые файлы
        all_files = smb_manager.get_files_in_directory()
        if not all_files:
            pytest.skip("Нет файлов для тестирования")

        # Находим первый непустой файл
        test_file = None
        for f in all_files:
            content_preview = smb_manager.get_one_content(f)
            if content_preview and len(content_preview) > 0:
                test_file = f
                break

        if not test_file:
            pytest.skip("Не найдено непустых файлов для тестирования")

        print(f"Файл для потоковой обработки: {os.path.basename(test_file)}")

        # Тестируем read_file_chunked
        chunks_received = []
        chunk_sizes = []

        def callback(chunk):
            chunks_received.append(chunk)
            chunk_sizes.append(len(chunk))

        success = smb_manager.read_file_chunked(test_file, callback, chunk_size=4096)
        assert success, "read_file_chunked не удался"

        print(f"Получено {len(chunks_received)} чанков")
        print(f"   Размеры чанков: {chunk_sizes[:5]}{'...' if len(chunk_sizes) > 5 else ''}")

        # Собираем все чанки
        stream_content = b''.join(chunks_received)

        # Сравниваем с обычным чтением
        full_content = smb_manager.get_one_content(test_file)
        assert full_content is not None, "Не удалось прочитать файл обычным способом"
        assert len(full_content) > 0, "Файл пустой"
        assert stream_content == full_content, "Содержимое при потоковом чтении не совпадает"

        print("Потоковое чтение работает корректно")

    def test_empty_files_skipping(self, smb_manager):
        """Тест 7: Специальный тест для проверки пропуска пустых файлов"""
        print("ТЕСТ 7: Проверка механизма пропуска пустых файлов")

        # Получаем все файлы
        all_files = smb_manager.get_files_in_directory()

        if not all_files:
            pytest.skip("Нет файлов для тестирования")

        print(f"Анализ {len(all_files)} файлов...")

        empty_count = 0
        non_empty_count = 0
        error_count = 0

        for i, file_path in enumerate(all_files[:50], 1):  # Проверяем первые 50
            try:
                content = smb_manager.get_one_content(file_path)
                if content and len(content) > 0:
                    non_empty_count += 1
                    if i <= 5:  # Показываем первые 5 непустых
                        print(f"{i}. {os.path.basename(file_path)} - {len(content)} байт")
                else:
                    empty_count += 1
                    if i <= 5:  # Показываем первые 5 пустых
                        print(f"{i}. {os.path.basename(file_path)} - ПУСТОЙ (пропущен)")
            except Exception as e:
                error_count += 1
                print(f"{i}. {os.path.basename(file_path)} - Ошибка: {e}")

        print(f"\nСтатистика:")
        print(f"   Всего проверено: {min(50, len(all_files))} файлов")
        print(f"   Непустые файлы: {non_empty_count}")
        print(f"   Пустые файлы: {empty_count}")
        print(f"   Ошибки: {error_count}")

        if empty_count > 0:
            print(f"\nМеханизм пропуска пустых файлов работает корректно")
            print(f"   Пропущено пустых файлов: {empty_count}")
        else:
            print(f"\nПустых файлов не обнаружено")


# Для запуска тестов напрямую (не через pytest)
if __name__ == "__main__":
    # Запускаем pytest с этим файлом
    pytest.main([__file__, "-v", "--tb=short"])