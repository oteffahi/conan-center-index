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
import functools

required_conan_version = ">=1.43.0"


class OpenblasConan(ConanFile):
    name = "openblas"
    description = "An optimized BLAS library based on GotoBLAS2 1.13 BSD version"
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.openblas.net"
    topics = ("blas", "lapack")
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_lapack": [True, False],
        "use_thread": [True, False],
        "dynamic_arch": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_lapack": False,
        "use_thread": True,
        "dynamic_arch": False,
    }

    def export_sources(self):
        copy(self, "CMakeLists.txt")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if hasattr(self, "settings_build") and cross_building(self, skip_x64_x86=True):
            raise ConanInvalidConfiguration("Cross-building not implemented")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        if self.options.build_lapack:
            self.output.warn("Building with lapack support requires a Fortran compiler.")
        tc.variables["NOFORTRAN"] = not self.options.build_lapack
        tc.variables["BUILD_WITHOUT_LAPACK"] = not self.options.build_lapack
        tc.variables["DYNAMIC_ARCH"] = self.options.dynamic_arch
        tc.variables["USE_THREAD"] = self.options.use_thread

        # Required for safe concurrent calls to OpenBLAS routines
        tc.variables["USE_LOCKING"] = not self.options.use_thread

        tc.variables["MSVC_STATIC_CRT"] = False  # don't, may lie to consumer, /MD or /MT is managed by conan

        # This is a workaround to add the libm dependency on linux,
        # which is required to successfully compile on older gcc versions.
        tc.variables["ANDROID"] = self.settings.os in ["Linux", "Android"]

        tc.generate()

    def build(self):
        if Version(self.version) >= "0.3.12":
            search = """message(STATUS "No Fortran compiler found, can build only BLAS but not LAPACK")"""
            replace = """message(FATAL_ERROR "No Fortran compiler found. Cannot build with LAPACK.")"""
        else:
            search = "enable_language(Fortran)"
            replace = """include(CheckLanguage)
check_language(Fortran)
if(CMAKE_Fortran_COMPILER)
  enable_language(Fortran)
else()
  message(FATAL_ERROR "No Fortran compiler found. Cannot build with LAPACK.")
  set (NOFORTRAN 1)
  set (NO_LAPACK 1)
endif()"""

        replace_in_file(self, os.path.join(self.source_folder, "cmake", "f_check.cmake"), search, replace)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, pattern="LICENSE", dst="licenses", src=self.source_folder)
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        # CMake config file:
        # - OpenBLAS always has one and only one of these components: openmp, pthread or serial.
        # - Whatever if this component is requested or not, official CMake imported target is always OpenBLAS::OpenBLAS
        # - TODO: add openmp component when implemented in this recipe
        self.cpp_info.set_property("cmake_file_name", "OpenBLAS")
        self.cpp_info.set_property("cmake_target_name", "OpenBLAS::OpenBLAS")
        self.cpp_info.set_property("pkg_config_name", "openblas")
        cmake_component_name = (
            "pthread" if self.options.use_thread else "serial"
        )  # TODO: ow to model this in CMakeDeps?
        self.cpp_info.components["openblas_component"].set_property("pkg_config_name", "openblas")
        self.cpp_info.components["openblas_component"].includedirs.append(os.path.join("include", "openblas"))
        self.cpp_info.components["openblas_component"].libs = collect_libs(self)
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["openblas_component"].system_libs.append("m")
            if self.options.use_thread:
                self.cpp_info.components["openblas_component"].system_libs.append("pthread")
            if self.options.build_lapack:
                self.cpp_info.components["openblas_component"].system_libs.append("gfortran")

        self.output.info("Setting OpenBLAS_HOME environment variable: {}".format(self.package_folder))
        self.env_info.OpenBLAS_HOME = self.package_folder

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.names["cmake_find_package"] = "OpenBLAS"
        self.cpp_info.names["cmake_find_package_multi"] = "OpenBLAS"
        self.cpp_info.components["openblas_component"].names["cmake_find_package"] = cmake_component_name
        self.cpp_info.components["openblas_component"].names[
            "cmake_find_package_multi"
        ] = cmake_component_name
