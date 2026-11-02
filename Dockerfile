FROM python:3.12-slim

WORKDIR /app
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ .

RUN useradd --create-home appuser
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "inventory.py"]
