# SlpDataEntry
A tool for easily importing and analyzing speech therapy data

# Dependencies
All dependencies arelisted in `ALL_DEBPENDENCIES.MD`.

## Virtual Environment
Pip dependecies are managed through [python-venv](https://docs.python.org/3/library/venv.html).

The virtual environment for this project is at `.venv`

**To create it:**

```sh
$ python3 -m venv .venv
```

**To activate it:**

```sh
$ source .venv/bin/activate
```

**To install the required dependecies in it:**

```sh
$ pip install -r pip_requirements.txt
```

**To update the requirements document:**

```sh
$ pip freeze > pip_requirements.txt
```