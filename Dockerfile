FROM python:3-slim

WORKDIR /usr/src/app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

USER 1000
COPY beats-exporter.py .
ENTRYPOINT [ "./beats-exporter.py" ]