from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file
import os

required_conan_version = ">=1.53.0"


class IttApiConan(ConanFile):
    name = "ittapi"
    description = (
        "The Instrumentation and Tracing Technology (ITT) API enables your application"
        " to generate and control the collection of trace data during its execution"
        " across different Intel tools."
    )
    license = ("BSD-3-Clause", "GPL-2.0-only")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/intel/ittapi"
    topics = ("itt", "vtune", "profiler", "profiling")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "ptmark": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "ptmark": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        # We have no C++ files, so we delete unused options.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        self._patch_sources()
        toolchain = CMakeToolchain(self)
        toolchain.variables["ITT_API_IPT_SUPPORT"] = self.options.ptmark
        toolchain.generate()

    def _patch_sources(self):
        # Don't force PIC
        replace_in_file(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            'set(CMAKE_C_FLAGS "${CMAKE_C_FLAGS} -fPIC")',
            "",
        )

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        if self.settings.os == "Windows":
            copy(self, "libittnotify.lib",
                 src=f"bin/{self.settings.build_type}",
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libittnotify.a",
                 src=os.path.join(self.source.folder, "bin"),
                 dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "BSD-3-Clause.txt",
             src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "GPL-2.0-only.txt",
             src=os.path.join(self.source_folder, "LICENSES"),
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        if self.settings.os == "Windows":
            self.cpp_info.libs = ["libittnotify"]
        else:
            self.cpp_info.libs = ["ittnotify"]
            self.cpp_info.system_libs = ["dl"]
