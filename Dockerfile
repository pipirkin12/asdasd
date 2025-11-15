# Используем официальный Python runtime
FROM python:3.12-slim

# Создаём рабочую директорию
WORKDIR /app

# Копируем файлы
COPY . .

# Устанавливаем зависимости
RUN pip install --no-cache-dir aiogram sqlite3

# Команда запуска
CMD ["python", "tveak.py"]
