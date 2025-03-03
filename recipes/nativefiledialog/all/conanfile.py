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

required_conan_version = ">=1.53.0"


class NativefiledialogConan(ConanFile):
    name = "nativefiledialog"
    description = "A tiny, neat C library that portably invokes native file open and save dialogs."
    license = "Zlib"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/mlabbe/nativefiledialog"
    topics = ("dialog", "gui")

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

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

        if self.settings.arch not in ["x86", "x86_64"]:
            raise ConanInvalidConfiguration(f"architecture {self.settings.arch} is not supported")

    def layout(self):
        basic_layout(self, src_folder="src")

    @property
    def _source_subfolder(self):
        return "source_subfolder"

    def requirements(self):
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("gtk/4.7.0")

    def build_requirements(self):
        self.tool_requires("premake/5.0.0-alpha15")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # TODO: fill in generate()
        tc = PkgConfigDeps(self)
        tc.generate()

    def build(self):
        if is_msvc(self):
            generator = "vs" + {
                "16": "2019",
                "15": "2017",
                "14": "2015",
                "12": "2013",
                "11": "2012",
                "10": "2010",
                "9": "2008",
                "8": "2005",
            }.get(str(self.settings.compiler.version))
        else:
            generator = "gmake2"
        subdir = os.path.join(self.source_folder, "build", "subdir")
        os.makedirs(subdir)
        with chdir(self, subdir):
            os.rename(os.path.join("..", "premake5.lua"), "premake5.lua")
            self.run(f"premake5 {generator}")

            if is_msvc(self):
                msbuild = MSBuild(self)
                msbuild.build("NativeFileDialog.sln")
            else:
                config = "debug" if self.settings.build_type == "Debug" else "release"
                config += "_x86" if self.settings.arch == "x86" else "_x64"
                env_build = AutoToolsBuildEnvironment(self)
                env_build.make(args=["config=%s" % config])

    def package(self):
        libname = "nfd_d" if self.settings.build_type == "Debug" else "nfd"
        if is_msvc(self):
            copy(self, f"*{libname}.lib",
                 dst=os.path.join(self.package_folder, "lib"),
                 src=self.source_folder,
                 keep_path=False)
        else:
            copy(self, f"*{libname}.a",
                 dst=os.path.join(self.package_folder, "lib"),
                 src=self.source_folder,
                 keep_path=False)
        copy(self, "*nfd.h",
             dst=os.path.join(self.package_folder, "include"),
             src=self.source_folder,
             keep_path=False)
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["nfd_d" if self.settings.build_type == "Debug" else "nfd"]
