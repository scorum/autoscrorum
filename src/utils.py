import os
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime


def which(file):
    for path in os.environ["PATH"].split(os.pathsep):
        if os.path.exists(os.path.join(path, file)):
            return os.path.join(path, file)
    return ''


@contextmanager
def write_to_tempfile(content):
    with tempfile.NamedTemporaryFile() as file:
        with open(file.name, 'w') as f:
            f.write(content)
        yield file.name


def fmt_time_from_now(secs=0):
    time_format = '%Y-%m-%dT%H:%M:%S%Z'
    return datetime.utcfromtimestamp(time.time() + int(secs)).strftime(time_format)


def to_date(date: str, fmt="%Y-%m-%dT%H:%M:%S"):
    return datetime.strptime(date, fmt)


def create_dir(path, rewrite=False):
    try:
        os.mkdir(path)
    except FileExistsError:
        if rewrite:
            remove_dir_tree(path)
            os.mkdir(path)


def create_temp_dir(path, prefix=""):
    return tempfile.mkdtemp(prefix=prefix, dir=path)


def remove_dir_tree(path):
    try:
        shutil.rmtree(path)
    except FileNotFoundError:
        pass


def remove_file(path):
    os.remove(path)
