FROM python:3.12

WORKDIR /code

# Copy the requirements file and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application code
COPY ./app /code/app

# Copy the wait_for_db script
COPY ./wait_for_db.py /code/wait_for_db.py

# Run the wait_for_db.py script before starting the app
CMD ["sh", "-c", "python /code/wait_for_db.py && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"]
