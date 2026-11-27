# Loader for the SM3 graphdb database: imports the Synthea data and runs a self-test (exit code 0 = OK)
FROM python:3.12-slim
WORKDIR /app
COPY src/setup_dbs/graphdb/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/setup_dbs/graphdb/ .
CMD ["python", "setup-graphdb.py"]
