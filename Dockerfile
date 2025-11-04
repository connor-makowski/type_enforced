# syntax = docker/dockerfile:1

## Uncomment the version of python you want to test against
# FROM python:3.11-slim
# FROM python:3.12-slim
FROM python:3.13-slim
# FROM python:3.14-slim
# # Temp Fix only needed for 3.14 until a wheel cffi is available
# RUN apt-get update && apt-get install -y gcc libffi-dev

# Set the working directory to /app
WORKDIR /app/

# Copy and install the requirements
# This includes egg installing the type_enforced package
COPY type_enforced/__init__.py /app/type_enforced/__init__.py
COPY pyproject.toml /app/pyproject.toml
COPY requirements.txt /app/requirements.txt
RUN pip install -r requirements.txt

# Drop into a shell by default
CMD ["/bin/bash"]
