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

required_conan_version = ">=1.33.0"


class UPXConan(ConanFile):
    name = "upx"
    description = "UPX - the Ultimate Packer for eXecutables "
    license = "GPL-2.0-or-later", "special-exception-for-compressed-executables"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://upx.github.io/"
    topics = ("packer", "executable", "compression", "size", "reduction", "small", "footprintt")
    no_copy_source = True
    settings = "os", "arch"

    def _conan_data_sources(self):
        # Don't surround this with try/catch to catch unknown versions
        conandata_version = self.conan_data["sources"][self.version]
        try:
            return conandata_version[str(self.settings.os)][str(self.settings.arch)]
        except KeyError:
            return None

    def validate(self):
        if not self._conan_data_sources():
            raise ConanInvalidConfiguration(
                f"This recipe has no upx binary for os/arch={self.settings.os}/{self.settings.arch}"
            )

    def build(self):
        tools.get(**self._conan_data_sources(), destination=self._source_subfolder, strip_root=True)

    def package(self):
        self.copy("LICENSE", src=self._source_subfolder, dst="licenses")
        self.copy("COPYING", src=self._source_subfolder, dst="licenses")
        if self.settings.os == "Windows":
            self.copy("upx.exe", src=self._source_subfolder, dst="bin")
        else:
            self.copy("upx", src=self._source_subfolder, dst="bin")

    def package_info(self):
        self.cpp_info.libdirs = []

        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.env_info.PATH.append(bin_path)

        bin_ext = ".exe" if self.settings.os == "Windows" else ""
        upx = os.path.join(bin_path, f"upx{bin_ext}")
        self.user_info.upx = upx
