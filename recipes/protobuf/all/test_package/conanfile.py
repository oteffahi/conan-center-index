from conan import ConanFile
from conan.tools.build import can_run, cross_building
from conan.tools.cmake import cmake_layout, CMake, CMakeToolchain
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        if cross_building(self) and hasattr(self, "settings_build"):
            self.tool_requires(self.tested_reference_str)

    def generate(self):
        VirtualRunEnv(self).generate()
        if cross_building(self) and hasattr(self, "settings_build"):
            VirtualBuildEnv(self).generate()
        else:
            VirtualRunEnv(self).generate(scope="build")
        tc = CMakeToolchain(self)
        tc.cache_variables["protobuf_LITE"] = self.dependencies[self.tested_reference_str].options.lite
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(bin_path, env="conanrun")
