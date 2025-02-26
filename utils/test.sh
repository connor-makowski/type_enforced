#!/bin/bash
python --version
for file in /app/test/*.py; do
    [ -e "$file" ] || continue  # Skip if no files match
    python "$file"
done