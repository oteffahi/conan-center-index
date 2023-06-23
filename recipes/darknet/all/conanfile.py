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


class DarknetConan(ConanFile):
    name = "darknet"
    license = "YOLO"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://pjreddie.com/darknet/"
    description = "Darknet is a neural network frameworks written in C"
    topics = ("neural network", "deep learning")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_opencv": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_opencv": False,
    }
    generators = "pkg_config"

    @property
    def _lib_to_compile(self):
        if not self.options.shared:
            return "$(ALIB)"
        else:
            return "$(SLIB)"

    @property
    def _shared_lib_extension(self):
        if self.settings.os == "Macos":
            return ".dylib"
        else:
            return ".so"

    def _patch_sources(self):
        apply_conandata_patches(self)
        replace_in_file(
            self,
            os.path.join(self.source_folder, "Makefile"),
            "SLIB=libdarknet.so",
            "SLIB=libdarknet" + self._shared_lib_extension,
        )
        replace_in_file(
            self,
            os.path.join(self.source_folder, "Makefile"),
            "all: obj backup results $(SLIB) $(ALIB) $(EXEC)",
            f"all: obj backup results {self._lib_to_compile}",
        )

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("This library is not compatible with Windows")

    def requirements(self):
        if self.options.with_opencv:
            self.requires("opencv/2.4.13.7")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        self._patch_sources()
        with chdir(self, self.source_folder):
            with environment_append(self, {"PKG_CONFIG_PATH": self.build_folder}):
                args = ["OPENCV={}".format("1" if self.options.with_opencv else "0")]
                env_build = AutoToolsBuildEnvironment(self)
                env_build.fpic = self.options.get_safe("fPIC", True)
                env_build.make(args=args)

    def package(self):
        copy(self, "LICENSE*", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(
            self,
            "*.h",
            dst=os.path.join(self.package_folder, "include"),
            src=os.path.join(self.source_folder, "include"),
        )
        copy(self, "*.so", dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.dylib", dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "*.a", dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["darknet"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["m", "pthread"]
        if stdcpp_library(self):
            self.cpp_info.system_libs.append(stdcpp_library(self))
