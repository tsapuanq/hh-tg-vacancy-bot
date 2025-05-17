import pandas as pd 
import ast
import logging
import re 
import numpy as np

def normalize_city_name(city: str) -> str:
    # пример: если вдруг получаем "Алмата", меняем на "Алматы"
    corrections = {
        'Алматы': 'Алматы',
        "Астане": "Астана",
        "Атырау": "Атырау",
        "Шымкенте": "Шымкент",
        "Костанае": "Костанай",
        "Актобе": "Актобе",
        "Караганде": "Караганда",
        "Таразе": "Тараз",
        "Щучинске": "Щучинск",
        "Усть-Каменогорске": "Усть-Каменогорск",
        "Семее": "Семей",
        "Павлодаре": "Павлодар",
        "Кокшетауе": "Кокшетау",
        "Талдыкоргане": "Талдыкорган",
        "Уральске": "Уральск"
    }
    return corrections.get(city, city)


def extract_city(pub_text: str) -> str:
    """
    Из строки вида
      "Вакансия опубликована 2 мая 2025 в Алматы"
    возвращает "Алматы".
    """
    if not pub_text or ' в ' not in pub_text:
        return None
    city = pub_text.split(' в ')[-1].strip()
    city = re.sub(r'[.,\s]+$', '', city)
    return city.capitalize()


# ======= working_hours =======
def clean_working_hours(hours_str: str) -> str:
    """
    Оставляем всё, что идёт после 'Рабочие часы' (с любым разделителем ':' или '：').
    Если значение пустое/NaN — возвращаем 'Не указано'.
    """
    if pd.isna(hours_str):
        return "Не указано"
    s = str(hours_str).strip()
    result = re.sub(r"(?i)^.*?рабочие часы[:：]?\s*", "", s)
    return result if result else "Не указано"


# ======= salary =======
def extract_salary_range_with_currency(salary_str):
    # 0) пустые и «Не указано»
    if pd.isna(salary_str) or "не указано" in str(salary_str).lower():
        return "Не указано"

    # 1) нормализуем строку
    text = str(salary_str).lower().replace("\xa0", " ").strip()

    # 2) определяем валюту
    if "₸" in text:
        currency = "₸"
    elif "₽" in text:
        currency = "₽"
    elif "$" in text or "usd" in text:
        currency = "$"
    elif "€" in text or "eur" in text:
        currency = "€"
    else:
        currency = ""

    # 3) пытаемся найти диапазон "от X до Y"
    m = re.search(r"от\s+([\d\s]+)\s*(?:₸|₽|\$|€)?\s*до\s+([\d\s]+)\s*(?:₸|₽|\$|€)?", text)
    if m:
        lo = m.group(1).replace(" ", "")
        hi = m.group(2).replace(" ", "")
        return f"{lo}-{hi} {currency}"

    # 4) "до Y"
    m = re.search(r"до\s+([\d\s]+)\s*(?:₸|₽|\$|€)?", text)
    if m:
        hi = m.group(1).replace(" ", "")
        return f"до {hi} {currency}"

    # 5) "от X"
    m = re.search(r"от\s+([\d\s]+)\s*(?:₸|₽|\$|€)?", text)
    if m:
        lo = m.group(1).replace(" ", "")
        return f"от {lo} {currency}"

    # 6) точная сумма без "от/до", но с валютой (например "400000 ₸")
    m = re.search(r"([\d\s]+)\s*(₸|₽|\$|€)", text)
    if m:
        amount = m.group(1).replace(" ", "")
        cur = m.group(2)
        return f"{amount} {cur}"

    # 7) на всякий случай: просто число (берём первое)
    m = re.search(r"([\d\s]+)", text)
    if m:
        amount = m.group(1).replace(" ", "")
        return f"{amount} {currency}"

    # 8) если ничего не подошло
    return "Не указано"



# ======= skills =======
def clean_skills(skills_str):
    try:
        skills = ast.literal_eval(skills_str)
        skills = [s.strip() for s in skills if isinstance(s, str) and s.strip()]
        return skills if skills else "Не указано"
    except:
        return "Не указано"


# ======= date =======
month_map = {
    "января": "01", "февраля": "02", "марта": "03", "апреля": "04",
    "мая": "05", "июня": "06", "июля": "07", "августа": "08",
    "сентября": "09", "октября": "10", "ноября": "11", "декабря": "12",
}

def parse_russian_date(date_str: str) -> pd.Timestamp:
    try:
        parts = date_str.strip().split()
        if len(parts) != 3:
            return pd.NaT
        day, month_rus, year = parts
        month = month_map.get(month_rus.lower())
        return (
            pd.to_datetime(
                f"{day.zfill(2)}.{month}.{year}", 
                format="%d.%m.%Y", 
                errors="coerce"
            ) if month else pd.NaT
        )
    except:
        return pd.NaT


# ======= work_format =======
def clean_work_format(text: str) -> str:
    if not isinstance(text, str):
        return "Не указано"
    return text.replace("Формат работы:", "").strip().capitalize() or "Не указано"



def clean_schedule(text):
    if isinstance(text, str):
        if 'График:' in text:
            return text.split('График:')[1].strip()
        elif 'Не указано' in text:
            return 'Не указано'
    return np.nan


# ======= Основной pipeline =======
def run_cleaning_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or not isinstance(df, pd.DataFrame):
        logging.warning("[Pipeline] Input is not a DataFrame.")
        return pd.DataFrame()
    if df.empty:
        logging.warning("[Pipeline] Пустой DataFrame — пропускаем очистку.")
        return df

    print(f"[DEBUG] Исходная форма: {df.shape}")
    print(f"[DEBUG] Колонки: {list(df.columns)}")

    # Удаляем пустые description
    df = df[df["description"].notna()].copy()
    print(f"[DEBUG] После фильтра по description: {df.shape}")

    # === Вырезаем старую очистку location и заменяем на новый код ===
    # df["location"] = df["location"].apply(clean_location)
    df["location"] = (
        df["location"]                      # изменено
        .apply(lambda x: extract_city(x))       # извлечение города
        .apply(lambda c: normalize_city_name(c))# нормализация
    )                                          # изменено

    # остальная очистка без изменений
    df["salary_range"]     = df["salary"].apply(extract_salary_range_with_currency)
    df["skills"]           = df["skills"].apply(clean_skills)
    df["published_date_dt"]= df["published_date"].apply(parse_russian_date)
    df["published_date_dt"]= df["published_date_dt"].dt.strftime("%Y-%m-%d")
    df["work_format"]      = df["work_format"].apply(clean_work_format)
    df["working_hours"]    = df["working_hours"].apply(clean_working_hours)
    df['schedule']         = df['schedule'].apply(clean_schedule)
    print(f"[DEBUG] Финальный DataFrame: {df.shape}")
    return df
