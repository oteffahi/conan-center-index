# TODO: verify the Conan v2 migration

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import copy, get

required_conan_version = ">=1.52.0"


class PortableFileDialogsConan(ConanFile):
    name = "portable-file-dialogs"
    description = "Portable GUI dialogs library, C++11, single-header"
    license = "WTFPL"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/samhocevar/portable-file-dialogs"
    topics = ("gui", "dialogs", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True
    no_copy_source = True

    def configure(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def layout(self):
        pass

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(
            self,
            "portable-file-dialogs.h",
            dst=os.path.join(self.package_folder, "include"),
            src=self.source_folder,
        )
        copy(self, "COPYING", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
