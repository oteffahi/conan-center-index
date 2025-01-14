from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, rmdir
from os import path

required_conan_version = ">=1.52.0"


class IntelNeon2sseConan(ConanFile):
    name = "intel-neon2sse"
    description = "Header only library intended to simplify ARM->IA32 porting"
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/intel/ARM_NEON_2_x86_SSE"
    topics = ("neon", "sse", "port", "translation", "intrinsics", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "SSE4": [True, False],
        "disable_performance_warnings": [True, False],
    }
    default_options = {
        "SSE4": False,
        "disable_performance_warnings": False,
    }
    no_copy_source = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.arch not in ("x86", "x86_64"):
            raise ConanInvalidConfiguration("neon2sse only supports arch={x86,x86_64}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE",
             dst=path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        rmdir(self, path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "NEON_2_SSE")
        self.cpp_info.set_property("cmake_target_name", "NEON_2_SSE::NEON_2_SSE")
        if self.options.SSE4:
            self.cpp_info.defines.append("USE_SSE4")
        if self.options.disable_performance_warnings:
            self.cpp_info.defines.append("NEON2SSE_DISABLE_PERFORMANCE_WARNING")

        # TODO: remove once generators for legacy generators is no longer needed
        self.cpp_info.names["cmake_find_package"] = "NEON_2_SSE"
        self.cpp_info.names["cmake_find_package_multi"] = "NEON_2_SSE"
