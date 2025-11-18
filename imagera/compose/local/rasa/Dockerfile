FROM python:3.10-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Rasa + TensorFlow stack
COPY requirements/rasa.txt /requirements/rasa.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /requirements/rasa.txt

# Rasa startup scripts
COPY ./compose/local/rasa/start /start-rasa
RUN sed -i 's/\r$//g' /start-rasa && chmod +x /start-rasa

# Copy only Rasa-related project files (or whole repo if easier)
COPY . /app

EXPOSE 5005
CMD ["/start-rasa"]
