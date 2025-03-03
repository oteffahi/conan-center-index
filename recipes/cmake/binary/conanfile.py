import os

from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.files import get, copy, rmdir
from conan.tools.scm import Version
from conan.errors import ConanInvalidConfiguration

required_conan_version = ">=1.51.0"


class CMakeConan(ConanFile):
    name = "cmake"
    description = "CMake, the cross-platform, open-source build system."
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/Kitware/CMake"
    topics = ("build", "installer", "pre-built")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        pass

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        if self.settings.arch not in ["x86_64", "armv8"]:
            raise ConanInvalidConfiguration(
                "CMake binaries are only provided for x86_64 and armv8 architectures"
            )

        if self.settings.os == "Windows" and self.settings.arch == "armv8" and Version(self.version) < "3.24":
            raise ConanInvalidConfiguration(
                "CMake only supports ARM64 binaries on Windows starting from 3.24"
            )

    def build(self):
        arch = str(self.settings.arch) if not is_apple_os(self) else "universal"
        get(self, **self.conan_data["sources"][self.version][str(self.settings.os)][arch], strip_root=True)

    def package(self):
        copy(self, "*",
             src=self.build_folder,
             dst=self.package_folder)

        if is_apple_os(self):
            docs_folder = os.path.join(self.build_folder, "CMake.app", "Contents", "doc", "cmake")
        else:
            docs_folder = os.path.join(self.build_folder, "doc", "cmake")

        copy(self, "Copyright.txt",
             src=docs_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

        if not is_apple_os(self):
            # Remove unneeded folders (also cause long paths on Windows)
            # Note: on macOS we don't want to modify the bundle contents
            #       to preserve signature validation
            rmdir(self, os.path.join(self.package_folder, "doc"))
            rmdir(self, os.path.join(self.package_folder, "man"))

    def package_info(self):
        self.cpp_info.frameworkdirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        if is_apple_os(self):
            bindir = os.path.join(self.package_folder, "CMake.app", "Contents", "bin")
            self.cpp_info.bindirs = [bindir]
        else:
            bindir = os.path.join(self.package_folder, "bin")

        # Needed for compatibility with v1.x - Remove when 2.0 becomes the default
        self.output.info(f"Appending PATH environment variable: {bindir}")
        self.env_info.PATH.append(bindir)
