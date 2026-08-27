FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY rincon_riichi_api ./rincon_riichi_api

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["uvicorn", "rincon_riichi_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
