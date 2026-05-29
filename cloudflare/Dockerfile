FROM python:3.12-slim

WORKDIR /app

COPY cloudflare/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY cloudflare/ .

CMD ["python", "updater.py"]
