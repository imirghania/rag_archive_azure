# One image for every job and app. The component is chosen by the command: python -m docai.modules.<module>
FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.7.3 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY search ./search
COPY prompts ./prompts
RUN uv sync --frozen --no-dev --extra azure

FROM python:3.12-slim
# Word and text to PDF conversion (job-digital) and TIFF/PDF rendering
RUN apt-get update && apt-get install -y --no-install-recommends libreoffice-writer fonts-dejavu fonts-noto-core \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY --from=build /app /app
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1
CMD ["python", "-c", "print('set the command: python -m docai.modules.<module>')"]
