from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, load, save, copy
import os

required_conan_version = ">=1.53.0"


class SofaConan(ConanFile):
    name = "sofa"
    description = "IAU Standards of Fundamental Astronomy (SOFA) C Library."
    license = "SOFA Software License"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://www.iausofa.org"
    topics = ("iau", "astronomy")

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
    def _sofa_src_dir(self):
        return os.path.join(self.source_folder, self.version, "c", "src")

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["SOFA_SRC_DIR"] = self._sofa_src_dir.replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_path.parent)
        cmake.build()

    def package(self):
        save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._get_license())
        cmake = CMake(self)
        cmake.install()

    def _get_license(self):
        sofa_header = load(self, os.path.join(self._sofa_src_dir, "sofa.h"))
        begin = sofa_header.find("/*----------------------------------------------------------------------")
        return sofa_header[begin:]

    def package_info(self):
        self.cpp_info.libs = ["sofa_c"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("m")
