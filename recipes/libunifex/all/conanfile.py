import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=1.52.0"


class LibunifexConan(ConanFile):
    name = "libunifex"
    description = "A prototype implementation of the C++ sender/receiver async programming model"
    license = ("Apache-2.0", "LLVM-exception")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/facebookexperimental/libunifex"
    topics = ("async", "cpp")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _minimum_standard(self):
        return 17

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "9",
            "clang": "10",
            "apple-clang": "11",
            "Visual Studio": "16",
            "msvc": "193",
        }

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        pass
        # TODO: port liburing to Conan v2
        # if self.settings.os in ["Linux", "FreeBSD"]:
        #     self.requires("liburing/2.2", transitive_headers=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._minimum_standard)

        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if not minimum_version:
            self.output.warning(
                f"{self.ref} requires C++{self._minimum_standard}. "
                f"Your compiler is unknown. Assuming it supports C++{self._minimum_standard}."
            )
        elif Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._minimum_standard}, which your compiler does not support."
            )

        if self.version == "cci.20220430" and is_msvc(self):
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on MSVC")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = False
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        self.cpp_info.set_property("cmake_file_name", "unifex")
        self.cpp_info.set_property("cmake_target_name", "unifex::unifex")
        self.cpp_info.set_property("pkg_config_name", "unifex")

        self.cpp_info.components["unifex"].libs = ["unifex"]
        self.cpp_info.components["unifex"].set_property("cmake_target_name", "unifex::unifex")

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.filenames["cmake_find_package"] = "unifex"
        self.cpp_info.filenames["cmake_find_package_multi"] = "unifex"
        self.cpp_info.names["cmake_find_package"] = "unifex"
        self.cpp_info.names["cmake_find_package_multi"] = "unifex"
        self.cpp_info.components["unifex"].names["cmake_find_package"] = "unifex"
        self.cpp_info.components["unifex"].names["cmake_find_package_multi"] = "unifex"

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["unifex"].system_libs = ["pthread"]
        #    self.cpp_info.components["unifex"].requires.append("liburing::liburing")
