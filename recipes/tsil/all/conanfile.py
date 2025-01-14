from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
from conan.tools.microsoft import is_msvc
import os

required_conan_version = ">=1.53.0"


class TsilConan(ConanFile):
    name = "tsil"
    description = "Two-loop Self-energy Integral Library"
    license = "GPL-2.0-or-later"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.niu.edu/spmartin/TSIL/"
    topics = ("high-energy", "physics", "hep", "two-loop", "integrals")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "size": ["long", "double"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "size": "long",
    }

    @property
    def _tsil_size(self):
        return "TSIL_SIZE_DOUBLE" if self.options.size == "double" else "TSIL_SIZE_LONG"

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if is_msvc(self):
            raise ConanInvalidConfiguration(f"TSIL does not support {self.settings.compiler}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TSIL_SRC_DIR"] = self.source_folder.replace("\\", "/")
        tc.variables["TSIL_SIZE"] = self.options.size
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_path.parent)
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["tsil"]
        self.cpp_info.defines.append(self._tsil_size)
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")

        # TODO: to remove in conan v2
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.env_info.PATH.append(bin_path)
