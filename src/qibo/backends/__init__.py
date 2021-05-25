import os
from qibo import config
from qibo.config import raise_error, log, warnings

# versions requirements
TF_MIN_VERSION = '2.2.0'


class Backend:

    def __init__(self):
        self.available_backends = {}
        active_backend = "numpy"

        # check if numpy is installed
        if self.check_availability("numpy"):
            from qibo.backends.numpy import NumpyBackend
            self.available_backends["numpy"] = NumpyBackend
        else:  # pragma: no cover
            raise_error(ModuleNotFoundError, "Numpy is not installed. "
                                             "Please install it using "
                                             "`pip install numpy`.")

        # check if tensorflow is installed and use it as default backend.
        if self.check_availability("tensorflow"):
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = str(config.LOG_LEVEL)
            import tensorflow as tf  # pylint: disable=E0401
            if tf.__version__ < TF_MIN_VERSION:  # pragma: no cover
                raise_error(
                    RuntimeError, f"TensorFlow version not supported, minimum is {TF_MIN_VERSION}.")
            from qibo.backends.tensorflow import TensorflowBackend
            self.available_backends["tensorflow"] = TensorflowBackend
            active_backend = "tensorflow"
            if self.check_availability("qibotf"):
                from qibo.backends.tensorflow import TensorflowCustomBackend
                self.available_backends["qibotf"] = TensorflowCustomBackend
                active_backend = "qibotf"
            else:  # pragma: no cover
                log.warning("qibotf library was not found. `tf.einsum` will be "
                            "used to apply gates. In order to install Qibo's "
                            "high performance custom operators please use "
                            "`pip install qibotf`.")
        else:  # pragma: no cover
            # case not tested because CI has tf installed
            log.warning("Tensorflow is not installed, falling back to numpy. "
                        "Numpy backend uses `np.einsum` and supports CPU only. "
                        "To enable GPU acceleration please install Tensorflow "
                        "with `pip install tensorflow`. To install the "
                        "optimized Qibo custom operators please use "
                        "`pip install qibotf` after installing Tensorflow.")

        self.constructed_backends = {}
        self._active_backend = None
        self.qnp = self.construct_backend("numpy")
        # Create the default active backend
        if "QIBO_BACKEND" in os.environ:  # pragma: no cover
            self.active_backend = os.environ.get("QIBO_BACKEND")
        self.active_backend = active_backend

    @property
    def active_backend(self):
        return self._active_backend

    @active_backend.setter
    def active_backend(self, name):
        self._active_backend = self.construct_backend(name)

    def construct_backend(self, name):
        """Constructs and returns a backend.

        If the backend already exists in previously constructed backends then
        the existing object is returned.

        Args:
            name (str): Name of the backend to construct.
                See ``available_backends`` for the list of supported names.

        Returns:
            Backend object.
        """
        if name not in self.constructed_backends:
            if name not in self.available_backends:
                available = [" - {}: {}".format(n, b.description)
                             for n, b in self.available_backends.items()]
                available = "\n".join(available)
                raise_error(ValueError, "Unknown backend {}. Please select one of "
                                        "the available backends:\n{}."
                                        "".format(name, available))
            new_backend = self.available_backends.get(name)()
            if self.active_backend is not None:
                new_backend.set_precision(self.active_backend.precision)
                if self.active_backend.default_device:
                    new_backend.set_device(self.active_backend.default_device)
            self.constructed_backends[name] = new_backend
        return self.constructed_backends.get(name)

    def __getattr__(self, x):
        return getattr(self.active_backend, x)

    def __str__(self):
        return self.active_backend.name

    def __repr__(self):
        return str(self)

    @staticmethod
    def check_availability(module_name):
        """Check if module is installed.

        Args:
            module_name (str): module name.

        Returns:
            True if the module is installed, False otherwise.
        """
        from pkgutil import iter_modules
        return module_name in (name for _, name, _ in iter_modules())


K = Backend()
numpy_matrices = K.qnp.matrices


def set_backend(backend="qibotf"):
    """Sets backend used for mathematical operations and applying gates.

    The following backends are available:
    'qibotf': Tensorflow backend with custom operators for applying gates,
    'tensorflow': Tensorflow backend that applies gates using ``tf.einsum``,
    'numpy': Numpy backend that applies gates using ``np.einsum``.

    Args:
        backend (str): A backend from the above options.
    """
    if not config.ALLOW_SWITCHERS and backend != K.name:
        warnings.warn("Backend should not be changed after allocating gates.",
                      category=RuntimeWarning)
    K.active_backend = backend


def get_backend():
    """Get backend used to implement gates.

    Returns:
        A string with the backend name.
    """
    return K.name


def set_precision(dtype='double'):
    """Set precision for states and gates simulation.

    Args:
        dtype (str): possible options are 'single' for single precision
            (complex64) and 'double' for double precision (complex128).
    """
    if not config.ALLOW_SWITCHERS and dtype != K.precision:
        warnings.warn("Precision should not be changed after allocating gates.",
                      category=RuntimeWarning)
    for bk in K.constructed_backends.values():
        bk.set_precision(dtype)
        bk.matrices.allocate_matrices()


def get_precision():
    """Get precision for states and gates simulation.

    Returns:
        A string with the precision name ('single', 'double').
    """
    return K.precision


def set_device(name):
    """Set default execution device.

    Args:
        name (str): Device name. Should follow the pattern
            '/{device type}:{device number}' where device type is one of
            CPU or GPU.
    """
    if not config.ALLOW_SWITCHERS and name != K.default_device:
        warnings.warn("Device should not be changed after allocating gates.",
                      category=RuntimeWarning)
    for bk in K.constructed_backends.values():
        bk.set_device(name)
        with bk.device(bk.default_device):
            bk.matrices.allocate_matrices()


def get_device():
    return K.default_device