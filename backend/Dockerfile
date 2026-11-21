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

# Hosting services may choose the port by setting PORT
ENV PORT=8000
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=30s \
    CMD python -c "import os, urllib.request as u; u.urlopen('http://localhost:%s/health' % os.environ['PORT'])"

# Bring the database up to date, get the demo account ready (if that fails,
# the API still starts), then serve. --proxy-headers: behind a host's proxy,
# take the visitor's address from it, for the sign-in limits
CMD ["sh", "-c", "alembic upgrade head && (python -m easyweight_api.demo || true) && exec uvicorn easyweight_api.main:app --host 0.0.0.0 --port $PORT --proxy-headers --forwarded-allow-ips='*'"]
