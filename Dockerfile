FROM mcr.microsoft.com/devcontainers/python:3.14

COPY requirements.txt .
COPY requirements_test.txt .

RUN pip3 install --no-cache-dir -r requirements.txt -r requirements_test.txt
