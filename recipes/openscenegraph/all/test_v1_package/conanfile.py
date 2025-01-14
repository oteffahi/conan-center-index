from conan.tools.apple import is_apple_os
from conans import CMake, ConanFile, tools
import os


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "cmake", "cmake_find_package_multi"

    def build(self):
        cmake = CMake(self)
        for key, value in self.options["openscenegraph"].items():
            if key.startswith("with_"):
                cmake.definitions["OSG_HAS_" + key.upper()] = 1 if value else 0
        if is_apple_os(self):
            cmake.definitions["OSG_HAS_WITH_GIF"] = 0
            cmake.definitions["OSG_HAS_WITH_JPEG"] = 0
            cmake.definitions["OSG_HAS_WITH_PNG"] = 0

        cmake.configure()
        cmake.build()

    def test(self):
        if not tools.cross_building(self):
            bin_path = os.path.join("bin", "test_package")
            self.run(bin_path, run_environment=True)
