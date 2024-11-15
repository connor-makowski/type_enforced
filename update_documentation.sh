
VERSION="1.8.0"
OLD_DOC_VERSIONS="1.7.0 1.6.0 1.5.0 1.4.0 1.3.0 1.2.0 1.1.1 0.0.16"

rm -r ./docs
python3 -m virtualenv venv
source venv/bin/activate

# If not in an venv, do not continue
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Not in a virtual environment. Exiting."
    exit 1
fi

export version_options="$VERSION $OLD_DOC_VERSIONS"

# generate the docs for a version function:
function generate_docs() {
    INPUT_VERSION=$1
    pdoc -o ./docs/$INPUT_VERSION -t ./doc_template type_enforced
}

pip install -r requirements.txt
generate_docs ./
generate_docs $VERSION

for version in $OLD_DOC_VERSIONS; do
    pip install ./dist/type_enforced-$version.tar.gz
    generate_docs $version
done;

pip install -e .