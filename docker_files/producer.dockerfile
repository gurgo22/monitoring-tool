FROM python:3.12-slim

WORKDIR /szakd

COPY producer.py .
COPY generated_file_1.json .
COPY generated_file_2.json .
COPY config.py .

RUN pip install redis

CMD ["python", "producer.py"]