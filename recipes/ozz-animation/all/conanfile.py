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


class OzzAnimationConan(ConanFile):
    name = "ozz-animation"
    description = "Open source c++ skeletal animation library and toolset."
    license = "MIT"
    topics = ("ozz", "animation", "skeletal")
    homepage = "https://github.com/guillaumeblanc/ozz-animation"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "fPIC": [True, False],
    }
    default_options = {
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        extracted_dir = self.name + "-" + self.version
        os.rename(extracted_dir, self.source_folder)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["ozz_build_fbx"] = False
        tc.variables["ozz_build_data"] = False
        tc.variables["ozz_build_samples"] = False
        tc.variables["ozz_build_howtos"] = False
        tc.variables["ozz_build_tests"] = False
        tc.variables["ozz_build_cpp11"] = True

    def build(self):
        for before, after in [
            ('string(REGEX REPLACE "/MT" "/MD" ${flag} "${${flag}}")', ""),
            ('string(REGEX REPLACE "/MD" "/MT" ${flag} "${${flag}}")', ""),
        ]:
            replace_in_file(
                self,
                os.path.join(self.source_folder, "build-utils", "cmake", "compiler_settings.cmake"),
                before,
                after,
            )

        replace_in_file(
            self,
            os.path.join(self.source_folder, "src", "animation", "offline", "tools", "CMakeLists.txt"),
            "if(NOT EMSCRIPTEN)",
            "if(NOT CMAKE_CROSSCOMPILING)",
        )

        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        os.remove(os.path.join(self.package_folder, "CHANGES.md"))
        os.remove(os.path.join(self.package_folder, "LICENSE.md"))
        os.remove(os.path.join(self.package_folder, "README.md"))
        copy(
            self,
            pattern="LICENSE.md",
            dst=os.path.join(self.package_folder, "licenses"),
            src=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
