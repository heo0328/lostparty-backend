FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt requirements-dev.txt requirements.in requirements-dev.in ./
COPY scripts/check_dependencies.py ./scripts/check_dependencies.py
RUN python scripts/check_dependencies.py && pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.txt \
    && pip check && python scripts/check_dependencies.py --installed runtime \
    && useradd --uid 10001 --create-home appuser
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini .
COPY --chown=appuser:appuser scripts/create_auth_keys.py ./scripts/create_auth_keys.py
USER appuser
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
