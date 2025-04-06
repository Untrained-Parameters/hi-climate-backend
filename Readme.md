# Setting up the environment

- Install the project python version using `pyenv`:

```bash
pyenv install $(cat .python-version)
```

- Configure and install poetry dependencies:

```bash
poetry config virtualenvs.in-project true #Optional

poetry env use $(cat .python-version)
poetry install
```
