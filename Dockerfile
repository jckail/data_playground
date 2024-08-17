FROM python:3.12

WORKDIR /code

# Copy the requirements file and install dependencies
COPY ./requirements.txt /code/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy the application code
COPY ./app /code/app

# Copy the Streamlit app
COPY ./streamlit_app.py /code/streamlit_app.py

# Copy the wait_for_db script
COPY ./wait_for_db.py /code/wait_for_db.py

# Copy the run_query script
COPY ./run_query.py /code/run_query.py

# Copy Alembic configuration and migration scripts
COPY ./alembic.ini /code/alembic.ini
COPY ./alembic /code/alembic

# Set the PYTHONPATH
ENV PYTHONPATH=/code

# Expose ports for FastAPI and Streamlit
EXPOSE 8000 8501

# Create a script to run both FastAPI and Streamlit
RUN echo '#!/bin/sh\n\
python /code/wait_for_db.py && \
alembic upgrade head && \
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload & \
streamlit run /code/streamlit_app.py --server.port 8501 --server.address 0.0.0.0\n\
wait' > /code/start.sh && chmod +x /code/start.sh

# Run the start script
CMD ["/code/start.sh"]