FROM python:3.11-bullseye
RUN apt-get update && apt-get install default-jre -y
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
COPY ./openapi.json /code/openapi.json
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
COPY ./generate-api.sh /code/generate-api.sh
RUN sh /code/generate-api.sh
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
