FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
COPY docs/assets ./docs/assets
# editable, so ui.py finds the logo in /app/docs/assets next to src/
RUN pip install --no-cache-dir -e .

ENV SHOULD_WE_HOST=0.0.0.0
VOLUME /app/data

EXPOSE 8080
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/')" || exit 1
CMD ["python", "-m", "should_we", "ui"]
