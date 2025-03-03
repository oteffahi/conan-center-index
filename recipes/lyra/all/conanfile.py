import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout

required_conan_version = ">=1.50.0"


class LyraConan(ConanFile):
    name = "lyra"
    description = (
        "A simple to use, composing, header only, command line arguments parser for C++ 11 and beyond."
    )
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://bfgroup.github.io/Lyra/"
    topics = (
        "cli",
        "cli-parser",
        "argparse",
        "commandline",
        "flags",
        "header-only",
        "no-dependencies",
        "c++11",
    )

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="root")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "*.h*",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "lyra")
        self.cpp_info.set_property("cmake_target_name", "bfg::lyra")
        # TODO: to remove in conan v2 once cmake_find_package* generators removed
        self.cpp_info.components["_lyra"].set_property("cmake_target_name", "bfg::lyra")
        self.cpp_info.filenames["cmake_find_package"] = "lyra"
        self.cpp_info.filenames["cmake_find_package_multi"] = "lyra"
        self.cpp_info.names["cmake_find_package"] = "bfg"
        self.cpp_info.names["cmake_find_package_multi"] = "bfg"
        self.cpp_info.components["_lyra"].names["cmake_find_package"] = "lyra"
        self.cpp_info.components["_lyra"].names["cmake_find_package_multi"] = "lyra"
        self.cpp_info.components["_lyra"].libdirs = []
        self.cpp_info.libdirs = []
