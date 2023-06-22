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
import functools
import os

required_conan_version = ">=1.43.0"


class SystemcConan(ConanFile):
    name = "systemc"
    description = """SystemC is a set of C++ classes and macros which provide
                     an event-driven simulation interface."""
    homepage = "https://www.accellera.org/"
    url = "https://github.com/conan-io/conan-center-index"
    license = "Apache-2.0"
    topics = ("simulation", "modeling", "esl", "tlm")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "disable_async_updates": [True, False],
        "disable_copyright_msg": [True, False],
        "disable_virtual_bind": [True, False],
        "enable_assertions": [True, False],
        "enable_immediate_self_notifications": [True, False],
        "enable_pthreads": [True, False],
        "enable_phase_callbacks": [True, False],
        "enable_phase_callbacks_tracing": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "disable_async_updates": False,
        "disable_copyright_msg": False,
        "disable_virtual_bind": False,
        "enable_assertions": True,
        "enable_immediate_self_notifications": False,
        "enable_pthreads": False,
        "enable_phase_callbacks": False,
        "enable_phase_callbacks_tracing": False,
    }

    generators = "cmake"

    @property
    def _is_msvc(self):
        return str(self.settings.compiler) in ["Visual Studio", "msvc"]

    def export_sources(self):
        self.copy("CMakeLists.txt")
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            self.copy(patch["patch_file"])

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            del self.options.enable_pthreads

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def validate(self):
        if self.settings.os == "Macos":
            raise ConanInvalidConfiguration("Macos build not supported")

        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration(
                "Building SystemC as a shared library on Windows is currently not supported"
            )

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True
        )

    @functools.lru_cache(1)
    def generate(self):
        cmake = CMake(self)
        cmake.definitions["DISABLE_ASYNC_UPDATES"] = self.options.disable_async_updates
        cmake.definitions["DISABLE_COPYRIGHT_MESSAGE"] = self.options.disable_copyright_msg
        cmake.definitions["DISABLE_VIRTUAL_BIND"] = self.options.disable_virtual_bind
        cmake.definitions["ENABLE_ASSERTIONS"] = self.options.enable_assertions
        cmake.definitions[
            "ENABLE_IMMEDIATE_SELF_NOTIFICATIONS"
        ] = self.options.enable_immediate_self_notifications
        cmake.definitions["ENABLE_PTHREADS"] = self.options.get_safe("enable_pthreads", False)
        cmake.definitions["ENABLE_PHASE_CALLBACKS"] = self.options.get_safe("enable_phase_callbacks", False)
        cmake.definitions["ENABLE_PHASE_CALLBACKS_TRACING"] = self.options.get_safe(
            "enable_phase_callbacks_tracing", False
        )
        cmake.configure()
        return cmake

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)
        self.copy("NOTICE", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SystemCLanguage")
        self.cpp_info.set_property("cmake_target_name", "SystemC::systemc")
        # TODO: back to global scope in conan v2 once cmake_find_package* generators removed
        self.cpp_info.components["_systemc"].libs = ["systemc"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["_systemc"].system_libs = ["pthread"]
        if self._is_msvc:
            self.cpp_info.components["_systemc"].cxxflags.append("/vmg")

        # TODO: to remove in conan v2 once cmake_find_package* generators removed
        self.cpp_info.filenames["cmake_find_package"] = "SystemCLanguage"
        self.cpp_info.filenames["cmake_find_package_multi"] = "SystemCLanguage"
        self.cpp_info.names["cmake_find_package"] = "SystemC"
        self.cpp_info.names["cmake_find_package_multi"] = "SystemC"
        self.cpp_info.components["_systemc"].names["cmake_find_package"] = "systemc"
        self.cpp_info.components["_systemc"].names["cmake_find_package_multi"] = "systemc"
        self.cpp_info.components["_systemc"].set_property("cmake_target_name", "SystemC::systemc")
