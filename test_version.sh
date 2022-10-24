deactivate > /dev/null
rm -rf venv > /dev/null
python$1 -m virtualenv venv > /dev/null
source venv/bin/activate > /dev/null
python$1 -m pip install -r requirements.txt > /dev/null
for f in test/*.py; do python$1 "$f"; done
deactivate
