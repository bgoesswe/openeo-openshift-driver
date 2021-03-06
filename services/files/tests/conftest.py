# Triggered before every pytest run to add the directory so that the service can be found
# by pytest
import os
import shutil
import sys
from os.path import abspath
from os.path import dirname

import pytest
from _pytest.fixtures import FixtureRequest


root_dir = dirname(dirname(abspath(__file__)))
sys.path.append(root_dir)


def get_data_folder() -> str:
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')


def get_input_folder() -> str:
    return os.path.join(get_data_folder(), 'input')


def get_tmp_folder() -> str:
    return os.path.join(get_data_folder(), 'tmp')


def get_filesystem_folder() -> str:
    return os.path.join(get_data_folder(), 'file-system')


os.environ['OEO_OPENEO_FILES_DIR'] = get_filesystem_folder()
os.environ['OEO_UPLOAD_TMP_DIR'] = get_tmp_folder()


@pytest.fixture()
def filesystem_folder() -> str:
    return get_filesystem_folder()


@pytest.fixture()
def tmp_folder(request: FixtureRequest) -> str:
    folder = get_tmp_folder()
    if not os.path.isdir(folder):
        os.makedirs(folder)

    def fin() -> None:
        if os.path.isdir(folder):
            shutil.rmtree(folder)
    request.addfinalizer(fin)

    return folder


@pytest.fixture()
def input_folder() -> str:
    return get_input_folder()


@pytest.fixture()
def user_folder(request: FixtureRequest) -> str:
    folder = os.path.join(get_filesystem_folder(), 'test-user')
    dirs_to_create = [os.path.join(folder, dir_name) for dir_name in ["files", "jobs"]]

    for d in dirs_to_create:
        if not os.path.exists(d):
            os.makedirs(d)

    def fin() -> None:
        shutil.rmtree(folder)
    request.addfinalizer(fin)
    return folder


@pytest.fixture()
def user_id() -> str:
    return 'test-user'


@pytest.fixture()
def upload_file() -> str:
    return os.path.join(get_input_folder(), 'upload.txt')
