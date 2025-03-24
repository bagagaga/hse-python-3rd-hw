FROM python:3.9

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH="/fastapi_app"

WORKDIR /fastapi_app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /fastapi_app/docker/*.sh
