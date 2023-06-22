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


class OpenTracingConan(ConanFile):
    name = "opentracing-cpp"
    description = "C++ implementation of the OpenTracing API http://opentracing.io"
    license = "Apache-2.0"
    topics = "opentracing"
    homepage = "https://github.com/opentracing/opentracing-cpp"
    url = "https://github.com/conan-io/conan-center-index"
    exports_sources = ["CMakeLists.txt", "patches/*.patch"]
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_mocktracer": [True, False],
        "enable_dynamic_load": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_mocktracer": False,
        "enable_dynamic_load": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        os.rename(self.name + "-" + self.version, self.source_folder)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_MOCKTRACER"] = self.options.enable_mocktracer
        tc.variables["BUILD_DYNAMIC_LOADING"] = self.options.enable_dynamic_load
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_STATIC_LIBS"] = not self.options.shared
        tc.variables["BUILD_TESTING"] = False
        tc.variables["ENABLE_LINTING"] = False
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def package(self):
        copy(self, "LICENSE", dst="licenses", src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.names["cmake_find_package"] = "OpenTracing"
        self.cpp_info.names["cmake_find_package_multi"] = "OpenTracing"

        target_suffix = "" if self.options.shared else "-static"
        lib_suffix = "" if self.options.shared or self.settings.os != "Windows" else "-static"
        # opentracing
        self.cpp_info.components["opentracing"].names["cmake_find_package"] = "opentracing" + target_suffix
        self.cpp_info.components["opentracing"].names["cmake_find_package_multi"] = (
            "opentracing" + target_suffix
        )
        self.cpp_info.components["opentracing"].libs = ["opentracing" + lib_suffix]
        if not self.options.shared:
            self.cpp_info.components["opentracing"].defines.append("OPENTRACING_STATIC")
        if self.options.enable_dynamic_load and self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.components["opentracing"].system_libs.append("dl")

        # opentracing_mocktracer
        if self.options.enable_mocktracer:
            self.cpp_info.components["opentracing_mocktracer"].names["cmake_find_package"] = (
                "opentracing_mocktracer" + target_suffix
            )
            self.cpp_info.components["opentracing_mocktracer"].names["cmake_find_package_multi"] = (
                "opentracing_mocktracer" + target_suffix
            )
            self.cpp_info.components["opentracing_mocktracer"].libs = ["opentracing_mocktracer" + lib_suffix]
            self.cpp_info.components["opentracing_mocktracer"].requires = ["opentracing"]
            if not self.options.shared:
                self.cpp_info.components["opentracing_mocktracer"].defines.append(
                    "OPENTRACING_MOCK_TRACER_STATIC"
                )
