import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=1.47.0"


class MPCGeneratorConan(ConanFile):
    name = "makefile-project-workspace-creator"
    description = "The Makefile, Project and Workspace Creator"
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/objectcomputing/MPC"
    topics = ("objectcomputing", "installer")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.settings.os == "Windows":
            self.requires("strawberryperl/5.32.1.1")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def build(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "*",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE",
            src=os.path.join(self.build_folder, "docs"),
            dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.frameworkdirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.includedirs = []

        bin_path = os.path.join(self.package_folder, "bin")
        self.buildenv_info.define("MPC_ROOT", bin_path)
        self.runenv_info.define("MPC_ROOT", bin_path)

        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.env_info.PATH.append(bin_path)
        self.env_info.MPC_ROOT = bin_path
