import os
import textwrap

from conan import ConanFile, conan_version
from conan.tools.files import copy, get, rmdir, save
from conan.tools.layout import basic_layout
from conan.tools.scm import Version

required_conan_version = ">=1.52.0"


class MesonConan(ConanFile):
    name = "meson"
    description = "Meson is a project to create the best possible next-generation build system"
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/mesonbuild/meson"
    topics = ("mesonbuild", "build-system", "pre-built")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.conf.get("tools.meson.mesontoolchain:backend", default="ninja", check_type=str) == "ninja":
            self.requires("ninja/1.11.1")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        pass

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        rmdir(self, os.path.join(self.package_folder, "bin", "test cases"))

        # create wrapper scripts
        save(
            self,
            os.path.join(self.package_folder, "bin", "meson.cmd"),
            textwrap.dedent("""\
            @echo off
            CALL python %~dp0/meson.py %*
        """),
        )
        save(
            self,
            os.path.join(self.package_folder, "bin", "meson"),
            textwrap.dedent("""\
            #!/usr/bin/env bash
            meson_dir=$(dirname "$0")
            exec "$meson_dir/meson.py" "$@"
        """),
        )

    @staticmethod
    def _chmod_plus_x(filename):
        if os.name == "posix":
            os.chmod(filename, os.stat(filename).st_mode | 0o111)

    def package_info(self):
        meson_root = os.path.join(self.package_folder, "bin")
        self._chmod_plus_x(os.path.join(meson_root, "meson"))
        self._chmod_plus_x(os.path.join(meson_root, "meson.py"))

        self.cpp_info.builddirs = [os.path.join("bin", "mesonbuild", "cmake", "data")]

        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.frameworkdirs = []
        self.cpp_info.resdirs = []

        if conan_version.major < 2:
            self.env_info.PATH.append(meson_root)
