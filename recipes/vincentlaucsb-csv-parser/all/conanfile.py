import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=1.52.0"


class VincentlaucsbCsvParserConan(ConanFile):
    name = "vincentlaucsb-csv-parser"
    description = "Vince's CSV Parser with simple and intuitive syntax"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/vincentlaucsb/csv-parser"
    topics = ("csv-parser", "csv", "rfc 4180", "parser", "generator", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def validate(self):
        # C++17 recommended: https://github.com/vincentlaucsb/csv-parser/blob/2.1.3/README.md
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)
        compiler = self.settings.compiler
        compiler_version = Version(self.settings.compiler.version)
        if compiler == "gcc" and compiler_version < "7":
            raise ConanInvalidConfiguration("gcc version < 7 not supported")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "*",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "single_include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.system_libs.append("pthread")
