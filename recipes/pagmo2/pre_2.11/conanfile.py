import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir

required_conan_version = ">=1.53.0"


class Pagmo2Conan(ConanFile):
    name = "pagmo2"
    description = "pagmo is a C++ scientific library for massively parallel optimization."
    license = ("LGPL-3.0-or-later", "GPL-3.0-or-later")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://esa.github.io/pagmo2"
    topics = ("pagmo", "optimization", "parallel-computing", "genetic-algorithm", "metaheuristics")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_eigen": [True, False],
        "with_nlopt": [True, False],
        "with_ipopt": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_eigen": False,
        "with_nlopt": False,
        "with_ipopt": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("boost/1.78.0")
        self.requires("onetbb/2020.3")
        if self.options.with_eigen:
            self.requires("eigen/3.4.0")
        if self.options.with_nlopt:
            self.requires("nlopt/2.7.1")

    def package_id(self):
        self.info.settings.clear()

    @property
    def _required_boost_components(self):
        return ["serialization"]

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)
        # TODO: add ipopt support
        if self.options.with_ipopt:
            raise ConanInvalidConfiguration("ipopt recipe not available yet in CCI")

        miss_boost_required_comp = any(
            self.dependencies["boost"].options.get_safe(f"without_{boost_comp}", True)
            for boost_comp in self._required_boost_components
        )
        if self.dependencies["boost"].options.header_only or miss_boost_required_comp:
            raise ConanInvalidConfiguration(
                "{0} requires non header-only boost with these components: {1}".format(
                    self.name, ", ".join(self._required_boost_components)
                )
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PAGMO_BUILD_TESTS"] = False
        tc.variables["PAGMO_BUILD_TUTORIALS"] = False
        tc.variables["PAGMO_WITH_EIGEN3"] = self.options.with_eigen
        tc.variables["PAGMO_WITH_NLOPT"] = self.options.with_nlopt
        tc.variables["PAGMO_WITH_IPOPT"] = self.options.with_ipopt
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING.*", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "pagmo")
        self.cpp_info.set_property("cmake_target_name", "Pagmo::pagmo")
        # TODO: back to global scope in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.components["_pagmo"].requires = [
            "boost::headers",
            "boost::serialization",
            "onetbb::onetbb",
        ]
        if self.options.with_eigen:
            self.cpp_info.components["_pagmo"].requires.append("eigen::eigen")
        if self.options.with_nlopt:
            self.cpp_info.components["_pagmo"].requires.append("nlopt::nlopt")
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["_pagmo"].system_libs.append("pthread")

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.filenames["cmake_find_package"] = "pagmo"
        self.cpp_info.filenames["cmake_find_package_multi"] = "pagmo"
        self.cpp_info.names["cmake_find_package"] = "Pagmo"
        self.cpp_info.names["cmake_find_package_multi"] = "Pagmo"
        self.cpp_info.components["_pagmo"].names["cmake_find_package"] = "pagmo"
        self.cpp_info.components["_pagmo"].names["cmake_find_package_multi"] = "pagmo"
        self.cpp_info.components["_pagmo"].set_property("cmake_target_name", "Pagmo::pagmo")
