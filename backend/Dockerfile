FROM python:3.14-slim
EXPOSE 8000
WORKDIR /backend
COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv
RUN uv sync --locked --no-dev --no-install-project
COPY . .
RUN uv sync --locked --no-dev
CMD ["uv", "run", "--no-sync", "fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
