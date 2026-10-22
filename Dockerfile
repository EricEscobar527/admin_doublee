FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=America/Mexico_City

WORKDIR /home/admin-doublee

RUN apt-get update -y \
    && apt-get install -y --no-install-recommends \
        gcc \
        pkg-config \
        default-libmysqlclient-dev \
        tzdata \
    && ln -sf /usr/share/zoneinfo/America/Mexico_City /etc/localtime \
    && echo "America/Mexico_City" > /etc/timezone \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . /home/admin-doublee
