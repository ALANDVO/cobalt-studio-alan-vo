FROM python:3.12-slim

RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin cobalt
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY backend/app /app/app
COPY VERSION /app/VERSION
RUN mkdir -p /data && chown -R cobalt:cobalt /app /data
USER cobalt
ENV PYTHONPATH=/app
ENV COBALT_DATABASE_PATH=/data/cobalt.sqlite
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health')"
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
