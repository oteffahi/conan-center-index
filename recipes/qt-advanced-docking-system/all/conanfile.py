import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rmdir
from conan.tools.scm import Version

required_conan_version = ">=1.56.0 <2 || >=2.0.6"


class QtADS(ConanFile):
    name = "qt-advanced-docking-system"
    description = (
        "Qt Advanced Docking System lets you create customizable layouts "
        "using a full featured window docking system similar to what is found "
        "in many popular integrated development environments (IDEs) such as "
        "Visual Studio."
    )
    license = "LGPL-2.1"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/githubuser0xFFFF/Qt-Advanced-Docking-System"
    topics = ("qt", "gui")

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
        return 14

    @property
    def _compilers_minimum_version(self):
        return {
            "Visual Studio": "15",
            "msvc": "191",
            "gcc": "5",
            "clang": "5",
            "apple-clang": "5.1",
        }

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

    def requirements(self):
        self.requires("qt/5.15.11", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.40")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler), False)
        if minimum_version and Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.ref} requires C++{self._min_cppstd}, which your compiler does not support."
            )

    def build_requirements(self):
        # Qt uses rcc during the build
        self.tool_requires("qt/<host_version>")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()
        tc = CMakeToolchain(self)
        tc.cache_variables["ADS_VERSION"] = self.version
        tc.variables["BUILD_EXAMPLES"] = "OFF"
        tc.variables["BUILD_STATIC"] = not self.options.shared
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)
        qt_version = self.dependencies["qt"].ref.version
        replace_in_file(self, os.path.join(self.source_folder, "src", "ads_globals.cpp"),
            "#include <qpa/qplatformnativeinterface.h>",
            f"#include <{qt_version}/QtGui/qpa/qplatformnativeinterface.h>",
        )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        rmdir(self, os.path.join(self.package_folder, "license"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["qtadvanceddocking"]
        else:
            self.cpp_info.defines.append("ADS_STATIC")
            self.cpp_info.libs = ["qtadvanceddocking_static"]
