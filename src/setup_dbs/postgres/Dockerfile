# Loader for the SM3 postgres database: imports the Synthea data and runs a self-test (exit code 0 = OK)
FROM python:3.12-slim
WORKDIR /app
COPY src/setup_dbs/postgres/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/setup_dbs/postgres/ .
CMD ["python", "setup-postgres.py"]
