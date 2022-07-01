"""
conftest.py

Pytest fixtures.
"""
import sys
import pytest
from qibo.backends import construct_backend


INACTIVE_TESTS = {
    "qibo.tests.test_backends_agreement",
    "qibo.tests.test_backends_init",
    "qibo.tests.test_backends_matrices",
    "qibo.tests.test_core_distcircuit_execution",
    "qibo.tests.test_core_distcircuit",
    "qibo.tests.test_core_distutils",
    "qibo.tests.test_core_measurements",
    "qibo.tests.test_core_states_distributed",
    "qibo.tests.test_core_states",
    "qibo.tests.test_models_qgan",
    "qibo.tests.test_models_variational",
    "qibo.tests.test_parallel"
}

# backends to be tested
BACKENDS = ["numpy", "tensorflow", "qibojit-numba", "qibojit-cupy"]


def get_backend(backend_name):
    if "-" in backend_name:
        name, platform = backend_name.split("-")
    else:
        name, platform = backend_name, None
    return construct_backend(name, platform=platform)

# ignore backends that are not available in the current testing environment
AVAILABLE_BACKENDS = []
for backend_name in BACKENDS:
    try:
        get_backend(backend_name)
        AVAILABLE_BACKENDS.append(backend_name)
    except (ModuleNotFoundError, ImportError):
        pass


def pytest_runtest_setup(item):
    ALL = {"darwin", "linux"}
    supported_platforms = ALL.intersection(
        mark.name for mark in item.iter_markers())
    plat = sys.platform
    if supported_platforms and plat not in supported_platforms:  # pragma: no cover
        # case not covered by workflows
        pytest.skip("Cannot run test on platform {}.".format(plat))


def pytest_configure(config):
    config.addinivalue_line("markers", "linux: mark test to run only on linux")


def pytest_addoption(parser):
    parser.addoption("--skip-parallel", action="store_true",
                     help="Skip tests that use the ``qibo.parallel`` module.")
    # parallel tests make the CI hang


@pytest.fixture
def backend(backend_name):
    yield get_backend(backend_name)


def pytest_generate_tests(metafunc):
    module_name = metafunc.module.__name__
    if module_name in INACTIVE_TESTS:
        pytest.skip()

    if "backend_name" in metafunc.fixturenames:
        metafunc.parametrize("backend_name", AVAILABLE_BACKENDS)

    if "accelerators" in metafunc.fixturenames:
        metafunc.parametrize("accelerators", [None])