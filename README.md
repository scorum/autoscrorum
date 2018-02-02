# Requirements
* pipenv
* python3.6

# Installing
``
git clone https://github.com/scorum/autoscrorum.git
cd autoscorum
./autoscorum.sh --install
``

# Running tests
``
./runner.sh
``

# Using pipenv

### Installing using pipenv
``
pipenv --python python3.6
pipenv run pip install -e .
``

### Runing testst with py.test
``
pipenv run py.test tests
``

# Development installation
```
git clone https://github.com/scorum/autoscrorum.git
git clone https://github.com/scorum/scorum-python.git
cd autoscorum
pipenv install
cd ../scorum-python
pipenv run pip install -e .
cd ../autoscorum -e .
```
