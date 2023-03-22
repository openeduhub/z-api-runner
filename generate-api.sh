#!/bin/bash
python -m venv chatgpt-api
rm -rf app/openapi_client
openapi-generator generate -g python -o edu_sharing_api -i https://repository.staging.openeduhub.net/edu-sharing/rest/openapi.json
cd edu_sharing_api && python setup.py install --user
cd ..
cp -r edu_sharing_api/openapi_client app/
rm -rf edu_sharing_api