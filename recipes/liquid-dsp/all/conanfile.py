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
from contextlib import contextmanager
import os

required_conan_version = ">=1.33.0"


class LiquidDspConan(ConanFile):
    name = "liquid-dsp"
    description = "Digital signal processing library for software-defined radios (and more)"
    topics = ("dsp", "sdr", "liquid-dsp")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/jgaeddert/liquid-dsp"
    license = ("MIT",)
    settings = "os", "arch", "build_type", "compiler"
    options = {
        "shared": [True, False],
        "simdoverride": [True, False],
    }
    default_options = {
        "shared": False,
        "simdoverride": False,
    }

    _autotools = None

    @property
    def _libname(self):
        if self.settings.os == "Windows":
            return "libliquid"
        return "liquid"

    @property
    def _target_name(self):
        if self.settings.os == "Macos":
            if not self.options.shared:
                return "libliquid.ar"
            return "libliquid.dylib"
        if not self.options.shared:
            return "libliquid.a"
        return "libliquid.so"

    @property
    def _lib_pattern(self):
        if self.settings.os == "Macos" and not self.options.shared:
            return "libliquid.a"
        if self.settings.os != "Windows":
            return self._target_name
        return "libliquid.lib"

    def export_sources(self):
        copy(self, "generate_link_library.bat", src=self.recipe_folder, dst=self.export_sources_folder)

    def configure(self):
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def build_requirements(self):
        if self._settings_build.os == "Windows" and not get_env(self, "CONAN_BASH_PATH"):
            self.build_requires("msys2/cci.latest")
        if self.settings.compiler == "Visual Studio":
            self.build_requires("mingw-w64/8.1")
            self.build_requires("automake/1.16.4")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if hasattr(self, "settings_build") and cross_building(self):
            raise ConanInvalidConfiguration("Cross building is not yet supported. Contributions are welcome")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _patch_sources(self):
        if self.settings.os == "Windows":
            apply_conandata_patches(self)

    def _gen_link_library(self):
        if self.settings.compiler != "Visual Studio" or (not self.options.shared):
            return
        self.run("cmd /c generate_link_library.bat")
        with chdir(self.source_folder):
            self.run(
                "{} /def:libliquid.def /out:libliquid.lib /machine:{}".format(
                    os.getenv("AR"), "X86" if self.settings.arch == "x86" else "X64"
                ),
                win_bash=tools.os_info.is_windows,
            )

    def _rename_libraries(self):
        with chdir(self.source_folder):
            if self.settings.os == "Windows" and self.options.shared:
                rename(self, "libliquid.so", "libliquid.dll")
            elif self.settings.os == "Windows" and not self.options.shared:
                rename(self, "libliquid.a", "libliquid.lib")
            elif self.settings.os == "Macos" and not self.options.shared:
                rename(self, "libliquid.ar", "libliquid.a")

    @contextmanager
    def _build_context(self):
        if self.settings.compiler == "Visual Studio":
            env = {
                "CC": "gcc",
                "CXX": "g++",
                "LD": "ld",
                "AR": "ar",
            }
            with environment_append(self, env):
                yield
        else:
            yield

    @contextmanager
    def _msvc_context(self):
        if self.settings.compiler == "Visual Studio":
            with vcvars(self.settings):
                env = {
                    "CC": "cl -nologo",
                    "CXX": "cl -nologo",
                    "AR": "lib",
                    "LD": "link",
                }
                with environment_append(self, env):
                    yield
        else:
            yield

    def build(self):
        self._patch_sources()
        ncpus = cpu_count(self)
        configure_args = []
        cflags = ["-static-libgcc"]
        if self.settings.build_type == "Debug":
            configure_args.append("--enable-debug-messages")
            cflags.extend(["-g", "-O0"])
        else:
            cflags.extend(["-s", "-O2", "-DNDEBUG"])
        if self.options.simdoverride:
            configure_args.append("--enable-simdoverride")
        if self.settings.compiler == "Visual Studio":
            configure_args.append("CFLAGS='{}'".format(" ".join(cflags)))
        configure_args_str = " ".join(configure_args)
        with self._build_context():
            with chdir(self.source_folder):
                self.run("./bootstrap.sh", win_bash=tools.os_info.is_windows)
                self.run("./configure {}".format(configure_args_str), win_bash=tools.os_info.is_windows)
                self.run("make {} -j{}".format(self._target_name, ncpus), win_bash=tools.os_info.is_windows)
        self._rename_libraries()
        with self._msvc_context():
            self._gen_link_library()

    def package(self):
        copy(
            self, pattern="LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses")
        )
        copy(
            self,
            pattern="liquid.h",
            dst=os.path.join("include", "liquid"),
            src=os.path.join(self.source_folder, "include"),
        )
        copy(
            self,
            pattern="libliquid.dll",
            dst=os.path.join(self.package_folder, "bin"),
            src=self.source_folder,
        )
        copy(
            self,
            pattern=self._lib_pattern,
            dst=os.path.join(self.package_folder, "lib"),
            src=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.libs = [self._libname]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs.append("m")
