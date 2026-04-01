FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY env/ env/
COPY baseline/ baseline/
COPY app.py .
COPY openenv.yaml .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV APP_MODE=ui

# Expose port for Gradio UI
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command: run UI or baseline based on APP_MODE
CMD ["sh", "-c", "if [ \"$APP_MODE\" = \"baseline\" ]; then python baseline/run_baseline.py; else python app.py; fi"]
