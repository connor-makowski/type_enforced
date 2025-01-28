#!/bin/bash
python --version
for f in /app/test/*.py; 
    do python "$f"; 
done