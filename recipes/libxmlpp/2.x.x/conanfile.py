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
from conan.tools.microsoft import is_msvc
import shutil
import os
import functools

required_conan_version = ">=1.45.0"


class LibXMLPlusPlus(ConanFile):
    # FIXME: naming the library "libxml++" causes conan not to add it to the
    # environment path on windows
    name = "libxmlpp"
    description = "libxml++ (a.k.a. libxmlplusplus) provides a C++ interface to XML files"
    license = "LGPL-2.1"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/libxmlplusplus/libxmlplusplus"
    topics = ["xml", "parser", "wrapper"]
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    generators = "pkg_config"

    @property
    def _build_subfolder(self):
        return "build_subfolder"

    def export_sources(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            self.copy(patch["patch_file"])

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def requirements(self):
        self.requires("libxml2/2.9.14")
        if tools.Version(self.version) <= "2.42.1":
            self.requires("glibmm/2.66.4")
        else:
            self.requires("glibmm/2.72.1")

    def validate(self):
        if hasattr(self, "settings_build") and tools.cross_building(self):
            raise ConanInvalidConfiguration("Cross-building not implemented")

        if self.settings.compiler.get_safe("cppstd"):
            tools.check_min_cppstd(self, 11)

    def build_requirements(self):
        self.build_requires("meson/0.63.0")
        self.build_requires("pkgconf/1.7.4")

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder
        )

    def _patch_sources(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)

        if is_msvc(self):
            # when using cpp_std=c++NM the /permissive- flag is added which
            # attempts enforcing standard conformant c++ code. the problem is
            # that older versions of the Windows SDK isn't standard conformant!
            # see:
            # https://developercommunity.visualstudio.com/t/error-c2760-in-combaseapih-with-windows-sdk-81-and/185399
            tools.replace_in_file(
                os.path.join(self._source_subfolder, "meson.build"), "cpp_std=c++", "cpp_std=vc++"
            )

    @functools.lru_cache(1)
    def _configure_meson(self):
        meson = Meson(self)
        defs = {
            "build-examples": "false",
            "build-tests": "false",
            "build-documentation": "false",
            "msvc14x-parallel-installable": "false",
            "default_library": "shared" if self.options.shared else "static",
        }
        meson.configure(
            defs=defs,
            build_folder=self._build_subfolder,
            source_folder=self._source_subfolder,
            pkg_config_paths=[self.install_folder],
        )
        return meson

    def build(self):
        self._patch_sources()
        with tools.environment_append(tools.RunEnvironment(self).vars):
            meson = self._configure_meson()
            meson.build()

    def package(self):
        lib_version = "2.6" if tools.Version(self.version) <= "2.42.1" else "5.0"

        self.copy("COPYING", dst="licenses", src=self._source_subfolder)
        meson = self._configure_meson()
        meson.install()

        shutil.move(
            os.path.join(
                self.package_folder, "lib", f"libxml++-{lib_version}", "include", "libxml++config.h"
            ),
            os.path.join(self.package_folder, "include", f"libxml++-{lib_version}", "libxml++config.h"),
        )

        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
        tools.rmdir(os.path.join(self.package_folder, "lib", f"libxml++-{lib_version}"))

        if is_msvc(self):
            tools.remove_files_by_mask(os.path.join(self.package_folder, "bin"), "*.pdb")
            if not self.options.shared:
                rename(
                    self,
                    os.path.join(self.package_folder, "lib", f"libxml++-{lib_version}.a"),
                    os.path.join(self.package_folder, "lib", f"xml++-{lib_version}.lib"),
                )

    def package_info(self):
        lib_version = "2.6" if tools.Version(self.version) <= "2.42.1" else "5.0"

        self.cpp_info.set_property("cmake_module_file_name", "libxml++")
        self.cpp_info.set_property("cmake_module_target_name", "libxml++::libxml++")
        self.cpp_info.set_property("pkg_config_name", "libxml++")
        self.cpp_info.components[f"libxml++-{lib_version}"].set_property(
            "pkg_config_name", f"libxml++-{lib_version}"
        )
        self.cpp_info.components[f"libxml++-{lib_version}"].libs = [f"xml++-{lib_version}"]
        self.cpp_info.components[f"libxml++-{lib_version}"].includedirs = [
            os.path.join("include", f"libxml++-{lib_version}")
        ]
        self.cpp_info.components[f"libxml++-{lib_version}"].requires = ["glibmm::glibmm", "libxml2::libxml2"]

        self.cpp_info.names["cmake_find_package"] = "libxml++"
        self.cpp_info.names["cmake_find_package_multi"] = "libxml++"
        self.cpp_info.names["pkg_config"] = "libxml++"
        self.cpp_info.components[f"libxml++-{lib_version}"].names["pkg_config"] = f"libxml++-{lib_version}"
