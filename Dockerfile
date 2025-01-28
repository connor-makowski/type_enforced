# syntax = docker/dockerfile:1
# FROM python:3.9-bookworm
# FROM python:3.10-bookworm
# FROM python:3.11-bookworm
# FROM python:3.12-bookworm
# FROM python:3.13-bookworm
FROM python:3.14-rc-bookworm

# Set python to unbuffered mode
ENV PYTHONUNBUFFERED=1

# Set the working directory to /app
WORKDIR /app/

# Copy and install the requirements
# This includes egg installing the type_enforced package
COPY type_enforced/__init__.py /app/type_enforced/__init__.py
COPY pyproject.toml /app/pyproject.toml
COPY requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY ./run_tests.sh /app/run_tests.sh
ENTRYPOINT ["/app/run_tests.sh"]