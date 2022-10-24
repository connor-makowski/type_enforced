deactivate
rm -rf venv
python$1 -m virtualenv venv
source venv/bin/activate
python$1 -m pip install -r requirements.txt
for f in test/*.py; do python$1 "$f"; done
deactivate
