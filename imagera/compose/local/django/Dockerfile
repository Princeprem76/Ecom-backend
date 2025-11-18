FROM python:3.10-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps for Django + psycopg
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gettext \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*

# Install Django/app deps (NO TF, NO Rasa)
COPY requirements/base.txt /requirements/base.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /requirements/base.txt

# Copy entry scripts
COPY ./compose/production/django/entrypoint /entrypoint
RUN sed -i 's/\r$//g' /entrypoint && chmod +x /entrypoint

COPY ./compose/local/django/start /start
RUN sed -i 's/\r$//g' /start && chmod +x /start

# Copy project code
COPY . /app

ENTRYPOINT ["/entrypoint"]
CMD ["/start"]
