#!/bin/bash

set -a # automatically export all variables
source .env
set +a

uvicorn main:app