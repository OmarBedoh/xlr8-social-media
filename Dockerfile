FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code only (NOT .env — credentials come from env vars)
COPY agent.py poster.py tools.py loop.py config.py ./

# Create all data directories in the persistent volume mount point
RUN mkdir -p /app/data/content/queue \
             /app/data/content/published \
             /app/data/content/slides \
             /app/data/Logs \
             /app/data/Tasks \
             /app/data/systems

ENV PYTHONUNBUFFERED=1
ENV BASE_PATH=/app/data

CMD ["python", "loop.py"]
