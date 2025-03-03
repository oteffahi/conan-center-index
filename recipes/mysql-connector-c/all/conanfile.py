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
import os

required_conan_version = ">=1.53.0"


class MysqlConnectorCConan(ConanFile):
    name = "mysql-connector-c"
    description = "A MySQL client library for C development."
    license = "GPL-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://dev.mysql.com/downloads/connector/c/"
    topics = ("mysql", "sql", "connector", "database")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ssl": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ssl": True,
        "with_zlib": True,
    }
    deprecated = "libmysqlclient"

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
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
        if self.options.with_ssl:
            self.requires("openssl/[>=1.1 <4]")

        if self.options.with_zlib:
            self.requires("zlib/1.3")

    def validate(self):
        if hasattr(self, "settings_build") and cross_building(self, skip_x64_x86=True):
            raise ConanInvalidConfiguration(
                "Cross compilation not yet supported by the recipe. Contributions are welcome."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["DISABLE_SHARED"] = not self.options.shared
        tc.variables["DISABLE_STATIC"] = self.options.shared
        # stack grows downwards, on very few platforms stack grows upwards
        tc.variables["STACK_DIRECTION"] = "-1"
        tc.variables["REQUIRE_STDCPP"] = stdcpp_library(self)
        if is_msvc(self):
            if not is_msvc_static_runtime(self):
                tc.variables["WINDOWS_RUNTIME_MD"] = True
        if self.options.with_ssl:
            tc.variables["WITH_SSL"] = "system"
        if self.options.with_zlib:
            tc.variables["WITH_ZLIB"] = "system"
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def _patch_sources(self):
        sources_cmake = os.path.join(self.source_folder, "CMakeLists.txt")
        sources_cmake_orig = os.path.join(self.source_folder, "CMakeListsOriginal.txt")
        rename(self, sources_cmake, sources_cmake_orig)
        rename(self, "CMakeLists.txt", sources_cmake)
        apply_conandata_patches(self)

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_path.parent)
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        mkdir(self, os.path.join(self.package_folder, "licenses"))
        rename(
            self,
            os.path.join(self.package_folder, "COPYING"),
            os.path.join(self.package_folder, "licenses", "COPYING"),
        )
        rename(
            self,
            os.path.join(self.package_folder, "COPYING-debug"),
            os.path.join(self.package_folder, "licenses", "COPYING-debug"),
        )
        rm("README*", self.package_folder, recursive=True)
        rm(self, "*.pdb", self.package_folder, recursive=True)
        rmdir(self, os.path.join(self.package_folder, "docs"))

    def package_info(self):
        self.cpp_info.libs = [
            "libmysql" if self.options.shared and self.settings.os == "Windows" else "mysqlclient"
        ]
        if not self.options.shared:
            stdcpp_library = stdcpp_library(self)
            if stdcpp_library:
                self.cpp_info.system_libs.append(stdcpp_library)
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.system_libs.append("m")
