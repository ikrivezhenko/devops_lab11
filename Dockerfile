# Этап сборки
FROM python:3.10-slim as builder

WORKDIR /app

COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Финальный этап
FROM python:3.10-slim

WORKDIR /app

# Копируем установленные пакеты из этапа сборки
COPY --from=builder /root/.local /root/.local
COPY app/ ./app/

# Делаем скрипты доступными
ENV PATH=/root/.local/bin:$PATH

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]