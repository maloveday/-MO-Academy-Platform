FROM python:3.12-slim

WORKDIR /srv/mo-academy/apps/api

COPY apps/api/pyproject.toml ./
RUN pip install --no-cache-dir \
    "fastapi>=0.115" "uvicorn[standard]>=0.30" "sqlalchemy>=2.0" \
    "alembic>=1.13" "pydantic-settings>=2.4" "pydantic[email]>=2.8" \
    "markdown>=3.6"

COPY packages/mo_teach/ /srv/mo-academy/packages/mo_teach/
RUN pip install --no-cache-dir /srv/mo-academy/packages/mo_teach

COPY apps/api/ ./
COPY apps/web/ /srv/mo-academy/apps/web/
COPY content/ /srv/mo-academy/content/
COPY labs/ /srv/mo-academy/labs/

EXPOSE 8000

# Idempotent migrations + curriculum seed, then serve.
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
