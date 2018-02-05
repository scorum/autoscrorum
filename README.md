# Requirements
* pipenv
* python3.6

# Installing
```bash
git clone https://github.com/scorum/autoscrorum.git
cd autoscorum
./autoscorum.sh --install
```

# Running tests
```bash
./runner.sh
```

# Using pipenv

### Installing using pipenv
```bash
git clone https://github.com/scorum/autoscrorum.git
cd autoscorum
pipenv --python python3.6
pipenv run pip install -e .
```

### Runing testst with py.test
```bash
pipenv run py.test tests
```

### Runing testst with runner.sh
```bash
./runner.sh {py_test_args_if_nedded} tests
```
