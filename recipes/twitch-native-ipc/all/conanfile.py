import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rename
from conan.tools.microsoft import is_msvc_static_runtime
from conan.tools.scm import Version

required_conan_version = ">=1.53.0"


class TwitchNativeIpcConan(ConanFile):
    name = "twitch-native-ipc"
    description = "Twitch native IPC library"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/twitchtv/twitch-native-ipc"
    topics = ("twitch", "ipc")

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
    def _compilers_min_version(self):
        return {
            "gcc": "8",
            "clang": "8",
            "apple-clang": "10",
            "msvc": "191",
            "Visual Studio": "15",
        }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, 17)

        min_version = self._compilers_min_version.get(str(self.settings.compiler), False)
        if min_version:
            if Version(self.settings.compiler.version) < min_version:
                raise ConanInvalidConfiguration("twitch-native-ipc requires C++17")
        else:
            self.output.warning("unknown compiler, assuming C++17 support")

        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("libuv/1.46.0")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_CODE_FORMATTING"] = False
        tc.variables["BUILD_TESTING"] = False
        if self.settings.os == "Windows":
            tc.variables["MSVC_DYNAMIC_RUNTIME"] = not is_msvc_static_runtime(self)
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "lib"), recursive=True)
        for dll in (self.package_path / "lib").glob("*.dll"):
            rename(self, dll, self.package_path / "bin" / dll.name)

    def package_info(self):
        self.cpp_info.libs = ["nativeipc"]
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.defines = ["NATIVEIPC_IMPORT"]

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs = ["m"]

        if stdcpp_library(self):
            self.cpp_info.system_libs.append(stdcpp_library(self))
