#!/bin/bash
python -m venv chatgpt-api
rm -rf app/openapi_client
#openapi-generator generate -g python -o edu_sharing_api -i https://repository.staging.openeduhub.net/edu-sharing/rest/openapi.json
openapi-generator generate -g python -o edu_sharing_api -i openapi.json
cd edu_sharing_api && \
  sed -i "s/self.client_side_validation = True/self.client_side_validation = False/g" openapi_client/configuration.py && \
  python setup.py install --user
cd ..
cp -r edu_sharing_api/openapi_client app/
rm -rf edu_sharing_api