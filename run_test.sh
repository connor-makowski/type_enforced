docker build . --tag "type_enforced" --quiet
docker run -it --rm \
    --volume "$(pwd):/app" \
    "type_enforced"

