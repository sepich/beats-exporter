FROM python:3.7-slim
ENV PYTHONDONTWRITEBYTECODE=true
ENV PYTHONUNBUFFERED=true

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

USER 1000
COPY beats-exporter.py .
ENTRYPOINT [ "./beats-exporter.py" ]