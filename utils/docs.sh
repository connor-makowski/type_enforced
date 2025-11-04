#!/bin/bash
cd /app/

# Make a temp init.py that only has the content below the __README_CONTENT_IS_COPIED_ABOVE__ line
cp README.md type_enforced/__init__.py
sed -i '1s/^/\"\"\"\n/' type_enforced/__init__.py
echo "\"\"\"" >> type_enforced/__init__.py
echo "from .enforcer import Enforcer, FunctionMethodEnforcer" >> type_enforced/__init__.py


# Specify versions for documentation purposes
VERSION="2.3.0"
OLD_DOC_VERSIONS="2.2.3 2.1.0 2.0.0 1.10.2 1.9.0 1.8.1 1.7.0 1.6.0 1.5.0 1.4.0 1.3.0 1.2.0 1.1.1 0.0.16"
export version_options="$VERSION $OLD_DOC_VERSIONS"

# generate the docs for a version function:
function generate_docs() {
    INPUT_VERSION=$1
    if [ $INPUT_VERSION != "./" ]; then
        if [ $INPUT_VERSION != $VERSION ]; then
            pip install "./dist/type_enforced-$INPUT_VERSION.tar.gz"
        fi
    fi
    pdoc -o ./docs/$INPUT_VERSION -t ./doc_template type_enforced
}

# Generate the docs for the current version
generate_docs ./
generate_docs $VERSION

# Generate the docs for all the old versions
for version in $OLD_DOC_VERSIONS; do
    generate_docs $version
done;

# Reinstall the current package as an egg
pip install -e .
