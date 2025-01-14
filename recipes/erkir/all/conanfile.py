from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.scm import Version
import os

required_conan_version = ">=1.54.0"


class ErkirConan(ConanFile):
    name = "erkir"
    description = "a C++ library for geodetic and trigonometric calculations"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/vahancho/erkir"
    topics = ("earth", "geodesy", "geography", "coordinate-systems", "geodetic", "datum")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    @property
    def _min_cppstd(self):
        return "11"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CODE_COVERAGE"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        if Version(self.version) < "2.0.0":
            copy(self, "*",
                 dst=os.path.join(self.package_folder, "include"),
                 src=os.path.join(self.source_folder, "include"))
            for pattern in ["*.lib", "*.a", "*.so", "*.dylib"]:
                copy(self, pattern,
                     src=self.build_folder,
                     dst=os.path.join(self.package_folder, "lib"),
                     keep_path=False)
            copy(self, "*.dll",
                 dst=os.path.join(self.package_folder, "bin"),
                 src=self.build_folder,
                 keep_path=False)
        else:
            cmake = CMake(self)
            cmake.install()
            rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
            rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "erkir")
        self.cpp_info.set_property("cmake_target_name", "erkir::erkir")
        postfix = "d" if Version(self.version) >= "2.0.0" and self.settings.build_type == "Debug" else ""
        self.cpp_info.libs = [f"erkir{postfix}"]
