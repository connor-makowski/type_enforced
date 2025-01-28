docker build . --tag "type_enforced" --quiet
docker run --rm \
    --volume "$(pwd):/app" \
    "type_enforced"

