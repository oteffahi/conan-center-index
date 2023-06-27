# TODO: verify the Conan v2 migration

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get

required_conan_version = ">=1.52.0"


class ProCxxBoostExSimdConan(ConanFile):
    name = "procxx-boost-ext-simd"
    description = "Portable SIMD computation library - was proposed as a Boost library"
    license = "BSL-1.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/procxx/boost.simd"
    topics = ("boost", "simd", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    no_copy_source = True

    @property
    def _min_cppstd(self):
        return "11"

    def layout(self):
        pass

    def requirements(self):
        self.requires("boost/1.76.0")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(
            self,
            pattern="*",
            dst=os.path.join(self.package_folder, "include"),
            src=os.path.join(self.source_folder, "include"),
        )
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []

        # this technique was inspired by conan-center's "boost-ex-ut" recipe,
        # and has been fixed to use the upstream Capitalized `Boost::`
        # namespace for components
        self.cpp_info.names["cmake_find_package"] = "Boost"
        self.cpp_info.names["cmake_find_package_multi"] = "Boost"

        # The original find_package() name here:
        self.cpp_info.filenames["cmake_find_package"] = "Boost.SIMD"
        self.cpp_info.filenames["cmake_find_package_multi"] = "Boost.SIMD"
        self.cpp_info.components["SIMD"].names["cmake_find_package"] = "SIMD"
        self.cpp_info.components["SIMD"].names["cmake_find_package_multi"] = "SIMD"
        self.cpp_info.components["SIMD"].requires = ["boost::headers"]
