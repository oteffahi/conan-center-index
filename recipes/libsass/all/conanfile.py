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
import re

required_conan_version = ">=1.53.0"


class LibsassConan(ConanFile):
    name = "libsass"
    description = "A C/C++ implementation of a Sass compiler"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "libsass.org"
    topics = ("Sass", "compiler")

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
    def _is_mingw(self):
        return self.settings.os == "Windows" and self.settings.compiler == "gcc"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def build_requirements(self):
        if self.settings.os != "Windows":
            self.tool_requires("libtool/2.4.7")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args += ["--disable-tests"]
        tc.generate()

    def _build_autotools(self):
        with chdir(self, self.source_folder):
            save(self, path="VERSION", content=f"{self.version}")
            self.run(f"{get_env(self, 'AUTORECONF')} -fiv")
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def _build_mingw(self):
        makefile = os.path.join(self.source_folder, "Makefile")
        replace_in_file(self, makefile, "CFLAGS   += -O2", "")
        replace_in_file(self, makefile, "CXXFLAGS += -O2", "")
        replace_in_file(self, makefile, "LDFLAGS  += -O2", "")
        with chdir(self, self.source_folder):
            env_vars = AutoToolsBuildEnvironment(self).vars
            env_vars.update(
                {
                    "BUILD": "shared" if self.options.shared else "static",
                    "PREFIX": unix_path(self, os.path.join(self.package_folder)),
                    # Don't force static link to mingw libs, leave this decision to consumer (through LDFLAGS in env)
                    "STATIC_ALL": "0",
                    "STATIC_LIBGCC": "0",
                    "STATIC_LIBSTDCPP": "0",
                }
            )
            with environment_append(self, env_vars):
                self.run(f"{self._make_program} -f Makefile")

    def _build_visual_studio(self):
        with chdir(self, self.source_folder):
            properties = {
                "LIBSASS_STATIC_LIB": "" if self.options.shared else "true",
                "WholeProgramOptimization": (
                    "true" if any(re.finditer("(^| )[/-]GL($| )", get_env(self, "CFLAGS", ""))) else "false"
                ),
            }
            platforms = {
                "x86": "Win32",
                "x86_64": "Win64",
            }
            msbuild = MSBuild(self)
            msbuild.build(os.path.join("win", "libsass.sln"), platforms=platforms, properties=properties)

    def build(self):
        if self._is_mingw:
            self._build_mingw()
        elif is_msvc(self):
            self._build_visual_studio()
        else:
            self._build_autotools()

    def _install_autotools(self):
        with chdir(self, self.source_folder):
            autotools = Autotools(self)
            autotools.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.la", self.package_folder, recursive=True)

    def _install_mingw(self):
        copy(
            self,
            "*.h",
            dst=os.path.join(self.package_folder, "include"),
            src=os.path.join(self.source_folder, "include"),
        )
        copy(
            self,
            "*.dll",
            dst=os.path.join(self.package_folder, "bin"),
            src=os.path.join(self.source_folder, "lib"),
        )
        copy(
            self,
            "*.a",
            dst=os.path.join(self.package_folder, "lib"),
            src=os.path.join(self.source_folder, "lib"),
        )

    def _install_visual_studio(self):
        copy(
            self,
            "*.h",
            dst=os.path.join(self.package_folder, "include"),
            src=os.path.join(self.source_folder, "include"),
        )
        copy(
            self,
            "*.dll",
            dst=os.path.join(self.package_folder, "bin"),
            src=os.path.join(self.source_folder, "win", "bin"),
            keep_path=False,
        )
        copy(
            self,
            "*.lib",
            dst=os.path.join(self.package_folder, "lib"),
            src=os.path.join(self.source_folder, "win", "bin"),
            keep_path=False,
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self._is_mingw:
            self._install_mingw()
        elif is_msvc(self):
            self._install_visual_studio()
        else:
            self._install_autotools()

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "libsass")
        self.cpp_info.libs = ["libsass" if is_msvc(self) else "sass"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["dl", "m"])
        if not self.options.shared and stdcpp_library(self):
            self.cpp_info.system_libs.append(stdcpp_library(self))
