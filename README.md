# Requirements
* pipenv

# Installing
```bash
git clone https://github.com/scorum/autoscrorum.git
cd autoscorum
./autoscorum.sh --install
```

# Ways to run tests:
* `./runner.sh --target={PATH} {py_test_args_if_nedded}` where PATH is absolute path to scorumd bin, or scorumd parent directory, or project build directory
* `./runner.sh --image={IMAGE} {py_test_args_if_nedded}` where IMAGE is image name in docker hub(**WARNING** image will be deleted from local docker storage and downloaded from docker hub) 
* `./runner.sh --image={IMAGE} --use-local-image {py_test_args_if_nedded}` where IMAGE is image name on your local docker storage

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
