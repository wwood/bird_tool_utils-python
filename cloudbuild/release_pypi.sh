if [ "${TWINE_PASSWORD}" == "" ]
then
    TWINE_PASSWORD=$(gcloud secrets versions access latest --secret="wwood-bird-tool-utils-pypi-api-token" --project=${PROJECT_ID})
fi

python3 -m pip install --upgrade build setuptools twine wheel
python3 -m build
python3 -m twine upload dist/*
