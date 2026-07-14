FROM python:3.12-slim

WORKDIR /szakd

COPY ./services ./services
COPY ./models ./models
COPY ./notification ./notification
COPY ./config.py ./config.py
COPY consumer.py consumer.py
COPY redis_utilities.py redis_utilities.py 

RUN pip install redis genson psycopg2-binary requests dotenv

CMD ["python", "-u", "consumer.py"]