# 1. Stage: Builder — здесь собираем зависимости
FROM python:3.10-slim AS builder

# Установка необходимых библиотек
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget gnupg ca-certificates fonts-liberation libnss3 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libxcomposite1 libxdamage1 libxrandr2 \
    libxkbcommon0 libxshmfence1 libgbm1 libgtk-3-0 libasound2 libx11-xcb1 libx11-6 \
    libxcb1 libxext6 libxfixes3 libxrender1 libxtst6 libexpat1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# Устанавливаем все зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Устанавливаем Playwright + браузеры
RUN pip install --no-cache-dir playwright
RUN playwright install --with-deps

# Теперь все зависимости готовы ✅

# ---------------------------------------------------------

# 2. Stage: Final — чистый финальный образ
FROM python:3.10-slim

# Установка только system-библиотек для работы браузера
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-liberation libnss3 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libxcomposite1 libxdamage1 libxrandr2 \
    libxkbcommon0 libxshmfence1 libgbm1 libgtk-3-0 libasound2 libx11-xcb1 libx11-6 \
    libxcb1 libxext6 libxfixes3 libxrender1 libxtst6 libexpat1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем только установленные пакеты из builder stage
COPY --from=builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Копируем код проекта
COPY ./scripts ./scripts
COPY ./data ./data
COPY run_all.py .

# Указываем команду запуска
CMD ["python", "run_all.py"]
