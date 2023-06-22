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
required_conan_version = ">=1.33.0"


class ForestDBConan(ConanFile):
    name = "forestdb"
    description = "ForestDB is a KeyValue store based on a Hierarchical B+-Tree."
    license = "Apache-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/ForestDB-KVStore/forestdb"
    topics = ("kv-store", "mvcc", "wal")
    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_snappy": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_snappy": False,
    }

    generators = "cmake"

    def export_sources(self):
        self.copy("CMakeLists.txt")
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            self.copy(patch["patch_file"])

    def requirements(self):
        if self.options.with_snappy:
            self.requires("snappy/1.1.9")

    def validate(self):
        if self.settings.os == "Windows":
            raise ConanInvalidConfiguration("Windows Builds Unsupported")
        if self.settings.compiler == "clang":
            if self.settings.compiler.libcxx == "libc++" and self.options.shared == False:
                raise ConanInvalidConfiguration("LibC++ Static Builds Unsupported")
        if self.settings.compiler.cppstd:
            tools.check_min_cppstd(self, 11)

    def configure(self):
        if self.options.shared:
            del self.options.fPIC

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder
        )

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        cmake = CMake(self)
        cmake.definitions["SNAPPY_OPTION"] = "Disable"
        if self.options.with_snappy:
            cmake.definitions["SNAPPY_OPTION"] = "Enable"
        cmake.configure()
        lib_target = "forestdb"
        if not self.options.shared:
            lib_target = "static_lib"
        cmake.build(target=lib_target)

    def package(self):
        self.copy("LICENSE", dst="licenses/", src=self._source_subfolder)
        # Parent Build system does not support library type selection
        # and will only install the shared object from cmake; so we must
        # handpick our libraries.
        self.copy("*.a*", dst="lib", src="lib")
        self.copy("*.lib", dst="lib", src="lib")
        self.copy("*.so*", dst="lib", src="lib", symlinks=True)
        self.copy("*.dylib*", dst="lib", src="lib", symlinks=True)
        self.copy("*.dll*", dst="lib", src="lib")
        self.copy("*.h", dst="include", src=os.path.join(self._source_subfolder, "include"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["forestdb"]
        self.cpp_info.system_libs.extend(["pthread", "m", "dl"])
        if self.settings.os == "Linux":
            self.cpp_info.system_libs.extend(["rt"])
