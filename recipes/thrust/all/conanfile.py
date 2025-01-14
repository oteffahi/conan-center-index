import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=1.52.0"


class ThrustConan(ConanFile):
    name = "thrust"
    description = (
        "Thrust is a parallel algorithms library which resembles the C++ Standard Template Library (STL)."
    )
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://thrust.github.io/"
    topics = ("parallel", "stl", "header-only", "cuda", "gpgpu")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "device_system": ["cuda", "cpp", "omp", "tbb"],
    }
    default_options = {
        "device_system": "tbb",
    }
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Otherwise CUB from system CUDA is used, which is not guaranteed to be compatible
        self.requires("cub/1.17.2")

        if self.options.device_system == "tbb":
            self.requires("onetbb/2021.10.0")

        if self.options.device_system in ["cuda", "omp"]:
            dev = str(self.options.device_system).upper()
            self.output.warning(
                f"Conan package for {dev} is not available, this package will use {dev} from system."
            )

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        for pattern in ["*.h", "*.inl"]:
            copy(self, pattern,
                 src=os.path.join(self.source_folder, "thrust"),
                 dst=os.path.join(self.package_folder, "include", "thrust"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        dev = str(self.options.device_system).upper()
        self.cpp_info.defines = [f"THRUST_DEVICE_SYSTEM=THRUST_DEVICE_SYSTEM_{dev}"]
        # Since CUB and Thrust are provided separately, their versions are not guaranteed to match
        self.cpp_info.defines += ["THRUST_IGNORE_CUB_VERSION_CHECK=1"]
