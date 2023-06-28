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

required_conan_version = ">=1.47.0"


class PlatformInterfacesConan(ConanFile):
    name = "platform.hashing"
    description = (
        "platform.hashing is one of the libraries of the LinksPlatform modular framework, "
        "which contains std::hash specializations for:\n"
        " - trivial and standard-layout types\n"
        " - types constrained by std::ranges::range\n"
        " - std::any"
    )
    license = "LGPL-3.0-only"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/linksplatform/Hashing"
    topics = ("linksplatform", "cpp20", "hashing", "any", "ranges", "native", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    @property
    def _minimum_cpp_standard(self):
        return 20

    @property
    def _internal_cpp_subfolder(self):
        return os.path.join(self.source_folder, "cpp", "Platform.Hashing")

    @property
    def _compilers_minimum_version(self):
        return {
            "gcc": "10",
            "Visual Studio": "16",
            "clang": "14",
            "apple-clang": "14",
        }

    def layout(self):
        pass

    def package_id(self):
        self.info.clear()

    def validate(self):
        minimum_version = self._compilers_minimum_version.get(str(self.settings.compiler))

        if not minimum_version:
            self.output.warning(
                f"{self.name} recipe lacks information about the {self.settings.compiler} compiler support."
            )

        elif Version(self.settings.compiler.version) < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.name}/{self.version} requires c++{self._minimum_cpp_standard}, which is not supported"
                f" by {self.settings.compiler} {self.settings.compiler.version}."
            )

        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._minimum_cpp_standard)

        if self.settings.arch in ("x86",):
            raise ConanInvalidConfiguration(f"{self.name} does not support arch={self.settings.arch}")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"), src=self._internal_cpp_subfolder)
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.libdirs = []
        suggested_flags = ""
        if not is_msvc(self):
            suggested_flags = {
                "x86_64": "-march=haswell",
                "armv7": "-march=armv7",
                "armv8": "-march=armv8-a",
            }.get(str(self.settings.arch), "")
        self.conf_info.define("user.platform.hashing:suggested_flags", suggested_flags)

        if "-march" not in "{} {}".format(os.environ.get("CPPFLAGS", ""), os.environ.get("CXXFLAGS", "")):
            self.output.warning(
                "platform.hashing needs to have `-march=ARCH` added to CPPFLAGS/CXXFLAGS. "
                "A suggestion is available in deps_user_info[{name}].suggested_flags.".format(name=self.name)
            )

        # TODO: to remove in conan v2
        self.user_info.suggested_flags = suggested_flags
