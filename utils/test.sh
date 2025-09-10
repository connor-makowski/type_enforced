#!/bin/bash
python --version

for file in "$(dirname "$0")"/../test/*.py; do
    [ -e "$file" ] || continue  # Skip if no files match
    python "$file"
done