FROM rasa/rasa-sdk:3.6.2

# Switch to root so we can install packages and chmod files
USER root

WORKDIR /app

# Install netcat for waitforit.sh (provides `nc`)
RUN apt-get update && apt-get install -y --no-install-recommends \
    netcat-openbsd \
    && rm -rf /var/lib/apt/lists/*
    
RUN pip install --no-cache-dir aiohttp
# Make sure the directory exists
RUN mkdir -p /app/compose

# Copy waitforit script and make it executable
COPY ./compose/waitforit.sh /app/compose/waitforit.sh
RUN chmod +x /app/compose/waitforit.sh

# Copy the start script into /app and make it executable
COPY ./compose/local/rasa/rasa_actions/start /app/start-rasa-action
RUN sed -i 's/\r$//g' /app/start-rasa-action && chmod +x /app/start-rasa-action

# Copy only the actions directory
COPY ./actions /app/actions

EXPOSE 5055

ENTRYPOINT ["/app/start-rasa-action"]
