FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY router/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY router/ .

CMD ["python", "router.py"]
