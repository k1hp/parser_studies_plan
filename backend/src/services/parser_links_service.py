import json
import os
from selenium import webdriver
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

import redis

BASE_URL = "https://mauniver.ru"

CURRENT_DIR = Path(__file__).resolve().parent

SELENIUM_URL = os.getenv("SELENIUM_URL", "http://selenium-chrome:4444/wd/hub")
REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))


# =========================================================
# DRIVER
# =========================================================

def setup_driver():

    options = webdriver.ChromeOptions()

    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Remote(
        command_executor=SELENIUM_URL,
        options=options
    )

    return driver


# =========================================================
# WAIT
# =========================================================

def wait_page(driver, timeout=10):

    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script(
            "return document.readyState"
        ) == "complete"
    )


# =========================================================
# СТРУКТУРА ИНСТИТУТОВ
# =========================================================

def get_structure(driver):

    driver.get(f"{BASE_URL}/structure/insts/")

    wait_page(driver)

    institutes = []

    visited_departments = set()

    headers = driver.find_elements(
        By.XPATH,
        "//div[contains(@class,'content')]//h2"
    )

    for h2 in headers:

        institute_name = h2.text.strip()

        if not institute_name:
            continue

        skip = [
            "образовательные подразделения",
            "факультеты",
            "центры",
            "филиалы"
        ]

        if any(x in institute_name.lower() for x in skip):
            continue

        departments = []

        current = h2

        while True:

            try:

                current = current.find_element(
                    By.XPATH,
                    "./following-sibling::*[1]"
                )

            except Exception:
                break

            if current.tag_name.lower() == "h2":
                break

            dept_links = current.find_elements(
                By.XPATH,
                ".//a[contains(@href, '/structure/kafs/')]"
            )

            for link in dept_links:

                dept_name = link.text.strip()

                dept_url = link.get_attribute("href")

                if not dept_name or not dept_url:
                    continue

                if dept_url in visited_departments:
                    continue

                visited_departments.add(dept_url)

                departments.append({
                    "name": dept_name,
                    "url": dept_url
                })

        if departments:

            institutes.append({
                "name": institute_name,
                "departments": departments
            })

    return institutes


# =========================================================
# ОТКРЫТЬ ПРОГРАММЫ КАФЕДРЫ
# =========================================================

def open_programs_page(driver, dept_url):

    driver.get(dept_url)

    wait_page(driver)

    try:

        link = driver.find_element(
            By.XPATH,
            "//a[contains(., 'Образовательные программы')]"
        )

        href = link.get_attribute("href")

        if not href:
            return False

        driver.get(href)

        wait_page(driver)

        return True

    except Exception:

        return False


# =========================================================
# ПАРСИНГ ПРОГРАММ
# =========================================================

def parse_programs(driver):

    programs = []

    try:

        table = driver.find_element(By.TAG_NAME, "table")

    except Exception:

        return programs

    rows = table.find_elements(By.TAG_NAME, "tr")

    for row in rows[1:]:

        try:

            cols = row.find_elements(By.TAG_NAME, "td")

            if len(cols) < 4:
                continue

            code = cols[0].text.strip()

            specialty = cols[1].text.strip()

            level = cols[2].text.strip()

            program_name = cols[3].text.strip()

            program_url = None

            links = row.find_elements(By.TAG_NAME, "a")

            for a in links:

                href = a.get_attribute("href")

                if not href:
                    continue

                if "/sveden/education/op/" in href:

                    program_url = href.split("#")[0]

                    break

            programs.append({
                "code": code,
                "specialty": specialty,
                "level": level,
                "program_name": program_name,
                "program_url": program_url
            })

        except Exception:
            continue

    return programs


# =========================================================
# ФУНКЦИЯ 1
# ПОЛНАЯ ИЕРАРХИЯ
# =========================================================

def get_hierarchy_json():

    driver = setup_driver()

    try:

        institutes = get_structure(driver)

        result = {
            "university": "Мурманский арктический университет",
            "institutes": {}
        }

        for institute in institutes:

            institute_name = institute["name"]

            result["institutes"][institute_name] = {}

            for dept in institute["departments"]:

                success = open_programs_page(
                    driver,
                    dept["url"]
                )

                if not success:
                    continue

                programs = parse_programs(driver)

                result["institutes"][institute_name][
                    dept["name"]
                ] = programs

        return result

    finally:

        try:
            driver.quit()
        except Exception:
            pass


# =========================================================
# ФУНКИЯ 2
# ПЛОСКИЙ MAP ДЛЯ REDIS
# =========================================================

def get_flat_mapping(hierarchy):

    import re

    flat = {}

    institutes = hierarchy["institutes"]

    for institute_name, departments in institutes.items():

        for dept_name, programs in departments.items():

            for program in programs:

                name = program["program_name"]
                url = program["program_url"]
                specialty = program.get("specialty", "")

                if not name or not url:
                    continue

                flat[name] = url

                # cleaned: убираем "(приём ...)" и обрезаем пробелы
                cleaned = re.sub(r'\s*\(приём\s[^)]+\)', '', name).strip()
                if cleaned and cleaned != name:
                    flat[cleaned] = url

                # specialty + profile (без годов)
                if specialty and cleaned != specialty:
                    combined = f"{specialty}, {cleaned}"
                    flat[combined] = url

    return flat


# =========================================================
# ФУНКЦИЯ 3
# НЕЧЁТКИЙ ПОИСК ПРОГРАММЫ В REDIS
# =========================================================

def find_program_url(query: str, min_score: float = 60.0) -> tuple[str | None, float]:

    from rapidfuzz import fuzz

    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )

    try:
        raw = r.get("flat_mapping")
    except redis.ResponseError:
        # ключ есть но не строка — удаляем
        r.delete("flat_mapping")
        return None, 0.0

    if not raw:
        return None, 0.0

    try:
        programs = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        r.delete("flat_mapping")
        return None, 0.0

    best_score = 0.0
    best_url = None

    q = query.lower()
    for name, url in programs.items():
        n = name.lower()
        score = max(fuzz.ratio(q, n), fuzz.partial_ratio(q, n))
        if score > best_score:
            best_score = score
            best_url = url

    if best_score >= min_score:
        return best_url, best_score
    return None, best_score


# =========================================================
# ФУНКЦИЯ 4
# ОБНОВЛЕНИЕ КЕША В REDIS
# =========================================================

def refresh_redis() -> dict:

    hierarchy = get_hierarchy_json()
    flat = get_flat_mapping(hierarchy)

    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )

    pipe = r.pipeline()
    pipe.delete("flat_mapping", "hierarchy")
    pipe.set("flat_mapping", json.dumps(flat, ensure_ascii=False))
    pipe.set("hierarchy", json.dumps(hierarchy, ensure_ascii=False))
    pipe.execute()

    return {"status": "ok", "flat_count": len(flat)}


# =========================================================
# MAIN
# =========================================================

if __name__ == "__main__":

    hierarchy = get_hierarchy_json()

    hierarchy_path = CURRENT_DIR / "hierarchy.json"

    with open(
        hierarchy_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            hierarchy,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("hierarchy.json saved")

    flat = get_flat_mapping(hierarchy)

    flat_path = CURRENT_DIR / "flat_mapping.json"

    with open(
        flat_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            flat,
            f,
            ensure_ascii=False,
            indent=2
        )

    print("flat_mapping.json saved")

    r = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
    )

    r.set("flat_mapping", json.dumps(flat, ensure_ascii=False))

    print(f"Redis: flat_mapping saved ({len(flat)} programs)")