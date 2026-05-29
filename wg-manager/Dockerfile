FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    wireguard-tools \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY wg-manager/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY wg-manager/ .

CMD ["python", "manager.py"]
