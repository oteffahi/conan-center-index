import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy


class SdbusCppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "PkgConfigDeps", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        if not self.conf.get("tools.gnu:pkg_config", default=False, check_type=str):
            self.tool_requires("pkgconf/1.9.5")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # workaround for https://gitlab.kitware.com/cmake/cmake/-/issues/18150
        copy(self, "*.pc",
             src=self.generators_folder,
             dst=os.path.join(self.generators_folder, "lib", "pkgconfig"))

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "example")
            self.run(bin_path, env="conanrun")
