docker build . --tag "type_enforced" --quiet > /dev/null
docker run -it --rm \
    --volume "$(pwd):/app" \
    "type_enforced"

