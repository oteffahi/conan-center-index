from conan import ConanFile
from conan.tools.apple import is_apple_os
from conan.tools.files import copy, get, symlinks
from conan.tools.scm import Version
from conan.errors import ConanInvalidConfiguration
import os

required_conan_version = ">=1.50.0"


class OpenJDK(ConanFile):
    name = "openjdk"
    description = "Java Development Kit builds, from Oracle"
    license = "GPL-2.0-with-classpath-exception"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://jdk.java.net"
    topics = ("java", "jdk", "openjdk", "pre-built")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        pass

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        if Version(self.version) < "19.0.2" and self.settings.arch != "x86_64":
            raise ConanInvalidConfiguration(
                "Unsupported Architecture.  This package currently only supports x86_64."
            )
        if self.settings.os not in ["Windows", "Macos", "Linux"]:
            raise ConanInvalidConfiguration(
                "Unsupported os. This package currently only support Linux/Macos/Windows"
            )

    def build(self):
        key = self.settings.os
        if is_apple_os(self):
            key = f"{self.settings.os}_{self.settings.arch}"
        get(self, **self.conan_data["sources"][self.version][str(key)], strip_root=True)

    def package(self):
        if is_apple_os(self):
            source_folder = os.path.join(self.source_folder, f"jdk-{self.version}.jdk", "Contents", "Home")
        else:
            source_folder = self.source_folder
        symlinks.remove_broken_symlinks(self, source_folder)
        copy(self, "*",
             src=os.path.join(source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             excludes=("msvcp140.dll", "vcruntime140.dll", "vcruntime140_1.dll"))
        copy(self, "*",
             src=os.path.join(source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*",
             src=os.path.join(source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*",
             src=os.path.join(source_folder, "jmods"),
             dst=os.path.join(self.package_folder, "lib", "jmods"))
        copy(self, "*",
             src=os.path.join(source_folder, "legal"),
             dst=os.path.join(self.package_folder, "licenses"))
        # conf folder is required for security settings, to avoid
        # java.lang.SecurityException: Can't read cryptographic policy directory: unlimited
        # https://github.com/conan-io/conan-center-index/pull/4491#issuecomment-774555069
        copy(self, "*",
             src=os.path.join(source_folder, "conf"),
             dst=os.path.join(self.package_folder, "conf"))

    def package_info(self):
        self.cpp_info.frameworkdirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.includedirs = []

        self.output.info(f"Creating JAVA_HOME environment variable with : {self.package_folder}")

        self.runenv_info.append("JAVA_HOME", self.package_folder)
        self.buildenv_info.append("JAVA_HOME", self.package_folder)

        # TODO: remove `env_info` once the recipe is only compatible with Conan >= 2.0
        self.env_info.JAVA_HOME = self.package_folder
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
