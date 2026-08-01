FROM python:3.13-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-cache-dir .

ENV SHOULD_WE_HOST=0.0.0.0
VOLUME /app/data

EXPOSE 8080
CMD ["python", "-m", "should_we", "ui"]
