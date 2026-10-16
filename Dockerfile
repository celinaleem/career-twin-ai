FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt requirements-data.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-data.txt
COPY app.py ./
COPY career_twin/ ./career_twin/
COPY scripts/ ./scripts/
COPY examples/ ./examples/
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.headless=true"]
