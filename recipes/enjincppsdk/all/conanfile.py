# TODO: verify the Conan v2 migration

import os

from conan import ConanFile, conan_version
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.android import android_abi
from conan.tools.apple import (
    XCRun,
    fix_apple_shared_install_name,
    is_apple_os,
    to_apple_arch,
)
from conan.tools.build import (
    build_jobs,
    can_run,
    check_min_cppstd,
    cross_building,
    default_cppstd,
    stdcpp_library,
    valid_min_cppstd,
)
from conan.tools.cmake import (
    CMake,
    CMakeDeps,
    CMakeToolchain,
    cmake_layout,
)
from conan.tools.env import (
    Environment,
    VirtualBuildEnv,
    VirtualRunEnv,
)
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    collect_libs,
    copy,
    download,
    export_conandata_patches,
    get,
    load,
    mkdir,
    patch,
    patches,
    rename,
    replace_in_file,
    rm,
    rmdir,
    save,
    symlinks,
    unzip,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfig,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import (
    MSBuild,
    MSBuildDeps,
    MSBuildToolchain,
    NMakeDeps,
    NMakeToolchain,
    VCVars,
    check_min_vs,
    is_msvc,
    is_msvc_static_runtime,
    msvc_runtime_flag,
    unix_path,
    unix_path_package_info_legacy,
    vs_layout,
)
from conan.tools.microsoft.visual import vs_ide_version
from conan.tools.scm import Version
from conan.tools.system import package_manager
import os
from conan.tools.cmake import (
    CMake,
    CMakeDeps,
    CMakeToolchain,
    cmake_layout,
)

required_conan_version = ">=1.43.0"


class EnjinCppSdk(ConanFile):
    name = "enjincppsdk"
    description = "A C++ SDK for development on the Enjin blockchain platform."
    license = "Apache-2.0"
    topics = ("enjin", "sdk", "blockchain")
    homepage = "https://github.com/enjin/enjin-cpp-sdk"
    url = "https://github.com/conan-io/conan-center-index"

    settings = "os", "compiler", "arch", "build_type"
    generators = "cmake", "cmake_find_package", "cmake_find_package_multi"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_default_http_client": [True, False],
        "with_default_ws_client": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_default_http_client": False,
        "with_default_ws_client": False,
    }
    short_paths = True

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    @property
    def _minimum_compilers_version(self):
        return {
            "Visual Studio": "16",
            "gcc": "9",
            "clang": "10",
        }

    def export_sources(self):
        self.copy("CMakeLists.txt")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

        if self.options.with_default_http_client:
            self.options["cpp-httplib"].with_openssl = True

        self.options["spdlog"].header_only = True

    def requirements(self):
        if self.options.with_default_http_client:
            self.requires("cpp-httplib/0.8.5")

        if self.options.with_default_ws_client:
            self.requires("ixwebsocket/11.0.4")

        self.requires("rapidjson/1.1.0")
        self.requires("spdlog/1.8.2")

    def build_requirements(self):
        self.build_requires("cmake/3.16.9")

    def validate(self):
        # Validations for OS
        if self.settings.os == "Macos":
            raise ConanInvalidConfiguration(
                "macOS is not supported at this time. Contributions are welcomed."
            )

        # Validations for minimum required C++ standard
        compiler = self.settings.compiler

        if compiler.get_safe("cppstd"):
            tools.check_min_cppstd(self, 17)

        minimum_version = self._minimum_compilers_version.get(str(compiler), False)
        if not minimum_version:
            self.output.warn(
                "C++17 support is required. Your compiler is unknown. Assuming it supports C++17."
            )
        elif tools.Version(compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                "C++17 support is required, which your compiler does not support."
            )

        if compiler == "clang" and compiler.libcxx != "libstdc++11":
            raise ConanInvalidConfiguration("libstdc++11 is required for clang.")

        # Validations for dependencies
        if not self.options["spdlog"].header_only:
            raise ConanInvalidConfiguration(f"{self.name} requires spdlog:header_only=True to be enabled.")

        if self.options.with_default_http_client and not self.options["cpp-httplib"].with_openssl:
            raise ConanInvalidConfiguration(
                f"{self.name} requires cpp-httplib:with_openssl=True when using "
                f"with_default_http_client=True."
            )

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True
        )

    def generate(self):

        tc = CMakeToolchain(self)
        tc.variables["ENJINSDK_BUILD_SHARED"] = self.options.shared
        tc.variables["ENJINSDK_BUILD_TESTS"] = False
        self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def build(self):
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="LICENSE*", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "enjinsdk"))

    def package_info(self):
        self.cpp_info.set_property("cmake_target_name", "enjinsdk::enjinsdk")
        self.cpp_info.names["cmake_find_package"] = "enjinsdk"
        self.cpp_info.names["cmake_find_package_multi"] = "enjinsdk"
        self.cpp_info.libs = ["enjinsdk"]
