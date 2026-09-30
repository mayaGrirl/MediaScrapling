FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir .

CMD ["crawler", "ui", "--host", "0.0.0.0", "--no-browser"]
