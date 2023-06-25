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
from conan.tools.scm import Version
from conan.tools.system import package_manager
from conan.tools.cmake import (
    CMake,
    CMakeDeps,
    CMakeToolchain,
    cmake_layout,
)

required_conan_version = ">=1.33.0"


class AndreasbuhrCppCoroConan(ConanFile):
    name = "andreasbuhr-cppcoro"
    description = "A library of C++ coroutine abstractions for the coroutines TS"
    topics = ("cpp", "async", "coroutines")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/andreasbuhr/cppcoro"
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"
    provides = "cppcoro"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    @property
    def _minimum_compilers_version(self):
        return {
            "Visual Studio": "15",
            "gcc": "10",
            "clang": "8",
            "apple-clang": "10",
        }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        # We can't simply check for C++20, because clang and MSVC support the coroutine TS despite not having labeled (__cplusplus macro) C++20 support
        min_version = self._minimum_compilers_version.get(str(self.settings.compiler))
        if not min_version:
            self.output.warn(
                "{} recipe lacks information about the {} compiler support.".format(
                    self.name, self.settings.compiler
                )
            )
        else:
            if Version(self.settings.compiler.version) < min_version:
                raise ConanInvalidConfiguration(
                    "{} requires coroutine TS support. The current compiler {} {} does not support it.".format(
                        self.name, self.settings.compiler, self.settings.compiler.version
                    )
                )

        # Currently clang expects coroutine to be implemented in a certain way (under std::experiemental::), while libstdc++ puts them under std::
        # There are also other inconsistencies, see https://bugs.llvm.org/show_bug.cgi?id=48172
        # This should be removed after both gcc and clang implements the final coroutine TS
        if self.settings.compiler == "clang" and self.settings.compiler.get_safe("libcxx") == "libstdc++":
            raise ConanInvalidConfiguration(
                "{} does not support clang with libstdc++. Use libc++ instead.".format(self.name)
            )

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = (
            self.settings.os == "Windows" and self.options.shared
        )
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE.txt", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.filenames["cmake_find_package"] = "cppcoro"
        self.cpp_info.filenames["cmake_find_package_multi"] = "cppcoro"
        self.cpp_info.names["cmake_find_package"] = "cppcoro"
        self.cpp_info.names["cmake_find_package_multi"] = "cppcoro"

        comp = self.cpp_info.components["cppcoro"]
        comp.names["cmake_find_package"] = "cppcoro"
        comp.names["cmake_find_package_multi"] = "cppcoro"
        comp.libs = ["cppcoro"]

        if self.settings.os == "Linux" and self.options.shared:
            comp.system_libs = ["pthread"]
        if self.settings.os == "Windows":
            comp.system_libs = ["synchronization"]

        if self.settings.compiler == "Visual Studio":
            comp.cxxflags.append("/await")
        elif self.settings.compiler == "gcc":
            comp.cxxflags.append("-fcoroutines")
            comp.defines.append("CPPCORO_COMPILER_SUPPORTS_SYMMETRIC_TRANSFER=1")
        elif self.settings.compiler == "clang" or self.settings.compiler == "apple-clang":
            comp.cxxflags.append("-fcoroutines-ts")
