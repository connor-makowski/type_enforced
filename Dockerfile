# syntax = docker/dockerfile:1

## Uncomment the version of python you want to test against
# FROM python:3.10-slim
# FROM python:3.11-slim
# FROM python:3.12-slim
FROM python:3.13-slim
# FROM python:3.14-rc-slim

# Set the working directory to /app
WORKDIR /app/

# Copy and install the requirements
# This includes egg installing the type_enforced package
COPY type_enforced/__init__.py /app/type_enforced/__init__.py
COPY pyproject.toml /app/pyproject.toml
RUN pip install -e .

COPY ./util_test_helper.sh /app/util_test_helper.sh
COPY ./test/test_fn_01.py /app/test/test_fn_01.py

CMD ["/bin/bash"]
# Comment out ENTRYPOINT to drop into an interactive shell for debugging when using test.sh
ENTRYPOINT ["/app/util_test_helper.sh"]
