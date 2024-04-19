#!/bin/bash
export PATH=/home/torsten/.jdks/corretto-21.0.2/bin/:$PATH
#python -m venv chatgpt-api
# pip install -r requirements.txt
rm -rf app/edu_sharing_api
wget https://repo1.maven.org/maven2/org/openapitools/openapi-generator-cli/7.4.0/openapi-generator-cli-7.4.0.jar -O openapi-generator-cli.jar
java -jar openapi-generator-cli.jar generate -g python-pydantic-v1 -o edu_sharing_api --skip-validate-spec -i https://repository.pre-staging.openeduhub.net/edu-sharing/rest/openapi.json --package-name edu_sharing_api
#openapi-generator generate -g python -o edu_sharing_api -i https://repository.staging.openeduhub.net/edu-sharing/rest/openapi.json --package-name edu_sharing_api
#openapi-generator generate -g python -o edu_sharing_api -i https://repository.pre-staging.openeduhub.net/edu-sharing/rest/openapi.json --package-name edu_sharing_api
#openapi-generator generate -g python -o edu_sharing_api -i openapi.json --package-name edu_sharing_api
cd edu_sharing_api && \
  sed -i "s/self.client_side_validation = True/self.client_side_validation = False/g" edu_sharing_api/configuration.py && \
  python setup.py install --user
cd ..
cp -r edu_sharing_api/edu_sharing_api app/
#rm -rf edu_sharing_api