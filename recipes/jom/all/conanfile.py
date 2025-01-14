import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, get

required_conan_version = ">=1.47.0"


class JomInstallerConan(ConanFile):
    name = "jom"
    description = (
        "jom is a clone of nmake to support the execution of multiple independent commands in parallel"
    )
    license = "GPL-3.0-only"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://wiki.qt.io/Jom"
    topics = ("build", "make", "makefile", "nmake", "pre-built")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        pass

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        if self.settings.os != "Windows":
            raise ConanInvalidConfiguration(f"{self.ref} only supports Windows")

    def source(self):
        pass

    def build(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        download(
            self,
            f"https://code.qt.io/cgit/qt-labs/jom.git/plain/LICENSE.GPL?h=v{self.version}",
            filename="LICENSE.GPL",
        )

    def package(self):
        copy(self, "LICENSE.GPL",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.exe",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.frameworkdirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

        # TODO: Legacy, to be removed on Conan 2.0
        bin_folder = os.path.join(self.package_folder, "bin")
        self.env_info.PATH.append(bin_folder)
