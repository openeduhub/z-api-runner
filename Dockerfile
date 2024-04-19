FROM python:3.11-bullseye
RUN apt-get update && apt-get install default-jre -y
WORKDIR /code
COPY ./requirements.txt /code/requirements.txt
COPY ./openapi.json /code/openapi.json
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
COPY ./app /code/app
COPY ./generate-api.sh /code/generate-api.sh
COPY ./generate-z-api.sh /code/generate-z-api.sh
RUN sh ./generate-api.sh
RUN sh ./generate-z-api.sh
RUN ls -alh && cd app && ls -alh
RUN ls -alh && cd app/z_api/models && ls -alh
WORKDIR /code/app
#CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "80"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
