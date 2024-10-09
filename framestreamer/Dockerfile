FROM python:3.12

COPY src /app/src/
COPY config.yaml /app/config.yaml
COPY requirements.txt /app/requirements.txt

WORKDIR /app

RUN pip install -r requirements.txt

ENTRYPOINT ["python3", "-m", "src.main"]
