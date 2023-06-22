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


class NudbConan(ConanFile):
    name = "nudb"
    license = "BSL-1.0"
    description = "A fast key/value insert-only database for SSD drives in C++11"
    homepage = "https://github.com/CPPAlliance/NuDB"
    url = "https://github.com/conan-io/conan-center-index/"
    topics = ("header-only", "KVS", "insert-only")
    no_copy_source = True

    def requirements(self):
        self.requires("boost/1.78.0")

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True
        )

    def package(self):
        self.copy("LICENSE*", "licenses", self._source_subfolder)
        self.copy("*.hpp", "include", src=os.path.join(self._source_subfolder, "include"))
        self.copy("*.ipp", "include", src=os.path.join(self._source_subfolder, "include"))

    def package_id(self):
        self.info.header_only()

    def package_info(self):
        self.cpp_info.names["cmake_find_package"] = "NuDB"
        self.cpp_info.names["cmake_find_package_multi"] = "NuDB"
        self.cpp_info.components["core"].names["cmake_find_package"] = "nudb"
        self.cpp_info.components["core"].names["cmake_find_package_multi"] = "nudb"
        self.cpp_info.components["core"].requires = ["boost::thread", "boost::system"]
        self.cpp_info.set_property("cmake_target_name", "NuDB")
        self.cpp_info.set_property("cmake_target_module_name", "NuDB::nudb")
        self.cpp_info.set_property("cmake_find_module", "both")
