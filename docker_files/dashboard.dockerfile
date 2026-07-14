FROM python:3.12-slim

WORKDIR /szakd

RUN pip install streamlit redis pandas plotly psycopg2-binary

COPY dashboard.py dashboard.py
COPY models ./models
COPY ./config.py ./config.py
COPY services ./services
COPY redis_utilities.py redis_utilities.py

EXPOSE 8501

ENTRYPOINT ["streamlit", "run", "dashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]