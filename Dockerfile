FROM mcr.microsoft.com/devcontainers/python:3.14

COPY requirements.txt .

RUN pip3 install -r requirements.txt
