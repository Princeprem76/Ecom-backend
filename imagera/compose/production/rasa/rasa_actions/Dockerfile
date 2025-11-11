FROM rasa/rasa-sdk:latest

WORKDIR /app

# Copy only the actions directory to the container
COPY ./imagera/rasachatbot/actions /app/actions

# Create the start-actions script inline and set permissions
RUN echo '#!/bin/bash\nexec rasa-sdk run --port 5055' > /app/start-actions && chmod +x /app/start-actions

EXPOSE 5055

# Command to run the custom action server
CMD ["/app/start-actions"]
