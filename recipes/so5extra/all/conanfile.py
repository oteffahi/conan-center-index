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

required_conan_version = ">=1.43.0"


class So5extraConan(ConanFile):
    name = "so5extra"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Stiffstream/so5extra"
    url = "https://github.com/conan-io/conan-center-index"
    description = "A collection of various SObjectizer's extensions."
    topics = ("concurrency", "actor-framework", "actors", "agents", "sobjectizer")
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def requirements(self):
        self.requires("sobjectizer/5.7.4")

    def validate(self):
        minimal_cpp_standard = "17"
        if self.settings.compiler.get_safe("cppstd"):
            tools.check_min_cppstd(self, minimal_cpp_standard)
        minimal_version = {
            "gcc": "7",
            "clang": "6",
            "apple-clang": "10",
            "Visual Studio": "15",
        }
        compiler = str(self.settings.compiler)
        if compiler not in minimal_version:
            self.output.warn(
                "%s recipe lacks information about the %s compiler standard version support"
                % (self.name, compiler)
            )
            self.output.warn(
                "%s requires a compiler that supports at least C++%s" % (self.name, minimal_cpp_standard)
            )
            return

        version = tools.Version(self.settings.compiler.version)
        if version < minimal_version[compiler]:
            raise ConanInvalidConfiguration(
                "%s requires a compiler that supports at least C++%s" % (self.name, minimal_cpp_standard)
            )

    def package_id(self):
        self.info.header_only()

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True
        )

    def package(self):
        self.copy(
            "*.hpp", dst="include/so_5_extra", src=os.path.join(self._source_subfolder, "dev", "so_5_extra")
        )
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "so5extra")
        self.cpp_info.set_property("cmake_target_name", "sobjectizer::so5extra")

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.filenames["cmake_find_package"] = "so5extra"
        self.cpp_info.filenames["cmake_find_package_multi"] = "so5extra"
        self.cpp_info.names["cmake_find_package"] = "sobjectizer"
        self.cpp_info.names["cmake_find_package_multi"] = "sobjectizer"
        self.cpp_info.components["so_5_extra"].names["cmake_find_package"] = "so5extra"
        self.cpp_info.components["so_5_extra"].names["cmake_find_package_multi"] = "so5extra"
        self.cpp_info.components["so_5_extra"].set_property("cmake_target_name", "sobjectizer::so5extra")
        self.cpp_info.components["so_5_extra"].requires = ["sobjectizer::sobjectizer"]
