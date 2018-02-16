# Requirements
* pipenv

# Installing
```bash
git clone https://github.com/scorum/autoscrorum.git
cd autoscorum
./autoscorum.sh --install
```

# Running tests
```bash
./runner.sh {py_test_args_if_nedded} tests
```

# Using pipenv

### Installing dev environment using pipenv
```bash
git clone https://github.com/scorum/autoscrorum.git
cd autoscorum
pipenv install
pipenv run pip install -e .
```

### Runing testst with py.test
```bash
pipenv run py.test tests
```
