FROM python:3.12

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt

RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ./app /code/app
COPY ./wait_for_db.py /code/wait_for_db.py

CMD ["sh", "-c", "python wait_for_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]