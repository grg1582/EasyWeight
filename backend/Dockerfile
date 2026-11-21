FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# Dependencies first, so editing the code doesn't reinstall them
COPY pyproject.toml ./
RUN mkdir -p easyweight_api/routers \
    && touch easyweight_api/__init__.py easyweight_api/routers/__init__.py \
    && pip install --no-cache-dir . \
    && rm -rf easyweight_api

COPY alembic.ini ./
COPY migrations ./migrations
COPY easyweight_api ./easyweight_api
RUN pip install --no-cache-dir --no-deps .

RUN useradd --create-home app
USER app

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Bring the database up to date, then serve
CMD ["sh", "-c", "alembic upgrade head && uvicorn easyweight_api.main:app --host 0.0.0.0 --port 8000"]
