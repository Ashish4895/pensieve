FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV PYTHONUNBUFFERED=1
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && python ingest_docs.py && gunicorn pensieve.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
