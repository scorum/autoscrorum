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
pipenv --python python3.6
pipenv run pip install -e .
```

### Runing testst with py.test
```bash
pipenv run py.test tests
```

# Development installation
```bash
git clone https://github.com/scorum/autoscrorum.git
git clone https://github.com/scorum/scorum-python.git
cd autoscorum
pipenv install
cd ../scorum-python
pipenv run pip install -e .
cd ../autoscorum -e .
```
