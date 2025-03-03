from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        if hasattr(self, "settings_build") and cross_building(self):
            self.tool_requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()
        if hasattr(self, "settings_build") and cross_building(self):
            VirtualBuildEnv(self).generate()
        else:
            VirtualRunEnv(self).generate(scope="build")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "addressbook")
            self.run(f"{bin_path} write", env="conanrun")
