#   Unexpected method '_configure_autotools'
#   Unexpected method '_detect_compilers'

# TODO: verify the Conan v2 migration

import os
import re

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
from conan.tools.cmake import (
    CMake,
    CMakeDeps,
    CMakeToolchain,
    cmake_layout,
)

required_conan_version = ">=1.53.0"


class AwsCdiSdkConan(ConanFile):
    name = "aws-cdi-sdk"
    description = "AWS Cloud Digital Interface (CDI) SDK"
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/aws/aws-cdi-sdk"
    topics = ("aws", "communication", "framework", "service")

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

    def export_sources(self):
        copy(self, "CMakeLists.txt", self.recipe_folder, self.export_sources_folder)
        export_conandata_patches(self)

    def configure(self):
        self.options["aws-libfabric"].shared = True
        self.options["aws-sdk-cpp"].shared = True

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("aws-libfabric/1.9.1amzncdi1.0")
        self.requires("aws-sdk-cpp/1.9.234")

    def validate(self):
        if self.settings.os not in ["Linux", "FreeBSD"]:
            raise ConanInvalidConfiguration(
                "This recipe currently only supports Linux. Feel free to contribute other platforms!"
            )
        if not self.dependencies["aws-libfabric"].options.shared or not self.dependencies["aws-sdk-cpp"].options.shared:
            raise ConanInvalidConfiguration("Cannot build with static dependencies")
        if not self.dependencies["aws-sdk-cpp"].options.get_safe("monitoring"):
            raise ConanInvalidConfiguration("This package requires the monitoring AWS SDK")
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()
        return self._autotools

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def _detect_compilers(self):
        cmake_cache = load(self, os.path.join(self.build_folder, "CMakeCache.txt"))
        cc = re.search("CMAKE_C_COMPILER:FILEPATH=(.*)", cmake_cache)[1]
        cxx = re.search("CMAKE_CXX_COMPILER:FILEPATH=(.*)", cmake_cache)[1]
        return cc, cxx

    def build(self):
        apply_conandata_patches(self)

        # build aws-cpp-sdk-cdi
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_path.parent)
        cmake.build()

        autotools = Autotools(self)
        autotools.configure()
        with chdir(self, self.source_folder):
            # configure autotools to find aws-cpp-sdk-cdi
            autotools.include_paths.append(
                os.path.join(self.build_folder, self.source_folder, "aws-cpp-sdk-cdi", "include")
            )
            autotools.library_paths.append(os.path.join(self.build_folder, "lib"))
            autotools.libs.append("aws-cpp-sdk-cdi")

            vars = autotools.vars
            cc, cxx = self._detect_compilers()
            vars["CC"] = cc
            vars["CXX"] = cxx
            if self.settings.build_type == "Debug":
                vars["DEBUG"] = "y"

            args = ["require_aws_sdk=no"]

            autotools.make(target="libsdk", vars=vars, args=args)

    def package(self):
        cmake = CMake(self)
        cmake.install()

        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, "*",
             dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "include"))
        config = "debug" if self.settings.build_type == "Debug" else "release"
        copy(self, "*",
             dst=os.path.join(self.package_folder, "lib"),
             src=os.path.join(self.source_folder, "build", config, "lib"))

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "aws-cdi-sdk")

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        # TODO: Remove the namespace on CMake targets
        self.cpp_info.names["cmake_find_package"] = "AWS"
        self.cpp_info.names["cmake_find_package_multi"] = "AWS"
        self.cpp_info.filenames["cmake_find_package"] = "aws-cdi-sdk"
        self.cpp_info.filenames["cmake_find_package_multi"] = "aws-cdi-sdk"

        cppSdk = self.cpp_info.components["aws-cpp-sdk-cdi"]
        cppSdk.libs = ["aws-cpp-sdk-cdi"]

        cppSdk.requires = ["aws-sdk-cpp::monitoring", "aws-libfabric::aws-libfabric"]

        cppSdk.set_property("cmake_target_name", "AWS::aws-cpp-sdk-cdi")
        cppSdk.set_property("pkg_config_name", "aws-cpp-sdk-cdi")

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        # TODO: Remove the namespace on CMake targets
        cppSdk.names["cmake_find_package"] = "aws-cpp-sdk-cdi"
        cppSdk.names["cmake_find_package_multi"] = "aws-cpp-sdk-cdi"

        cSdk = self.cpp_info.components["cdisdk"]
        cSdk.libs = ["cdisdk"]
        cSdk.requires = ["aws-cpp-sdk-cdi"]
        if self.settings.os in ["Linux", "FreeBSD"]:
            cSdk.defines = ["_LINUX"]

        cSdk.set_property("cmake_target_name", "AWS::aws-cdi-sdk")
        cSdk.set_property("pkg_config_name", "aws-cdi-sdk")

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        # TODO: Remove the namespace on CMake targets
        cSdk.names["cmake_find_package"] = "aws-cdi-sdk"
        cSdk.names["cmake_find_package_multi"] = "aws-cdi-sdk"
