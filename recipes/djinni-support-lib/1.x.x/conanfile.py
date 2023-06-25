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
from conan.tools.cmake import (
    CMake,
    CMakeDeps,
    CMakeToolchain,
    cmake_layout,
)


class DjinniSuppotLib(ConanFile):
    name = "djinni-support-lib"
    homepage = "https://djinni.xlcpp.dev"
    url = "https://github.com/conan-io/conan-center-index"
    description = "Djinni is a tool for generating cross-language type declarations and interface bindings"
    topics = ("java", "Objective-C", "Android", "iOS")
    license = "Apache-2.0"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "target": ["jni", "objc", "python", "cppcli", "auto", "deprecated"],
        "with_jni": [True, False, "auto"],
        "with_objc": [True, False, "auto"],
        "with_python": [True, False, "auto"],
        "with_cppcli": [True, False, "auto"],
        "system_java": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "target": "deprecated",
        "with_jni": "auto",
        "with_objc": "auto",
        "with_python": "auto",
        "with_cppcli": "auto",
        "system_java": False,
    }

    @property
    def _objc_support(self):
        if self.options.with_objc == "auto" or self.options.target == "auto":
            return is_apple_os(self.settings.os)
        else:
            return self.options.with_objc == True or self.options.target == "objc"

    @property
    def _jni_support(self):
        if self.options.with_jni == "auto" or self.options.target == "auto":
            return self.settings.os == "Android"
        else:
            return self.options.with_jni == True or self.options.target == "jni"

    @property
    def _python_support(self):
        return self.options.with_python == True or self.options.target == "python"

    @property
    def _cppcli_support(self):
        if self.options.with_cppcli == "auto" or self.options.target == "auto":
            return self.settings.os == "Windows"
        else:
            return self.options.with_cppcli == True or self.options.target == "cppcli"

    def configure(self):
        if self.settings.compiler == "Visual Studio" or self.options.shared:
            self.options.rm_safe("fPIC")

    def build_requirements(self):
        if not self.options.system_java and self._jni_support:
            self.build_requires("zulu-openjdk/11.0.12@")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        elif self.settings.os == "Android":
            self.options.system_java = True

    @property
    def _supported_compilers(self):
        return {
            "gcc": "8",
            "clang": "7",
            "Visual Studio": "15",
            "apple-clang": "10",
        }

    def validate(self):
        if self.options.target != "deprecated":
            self.output.warn(
                "The 'target' option is deprecated and will be removed soon. Use 'with_jni', 'with_objc', 'with_python' or 'with_cppcli' options instead."
            )
        if not (self._objc_support or self._jni_support or self._python_support or self._cppcli_support):
            raise ConanInvalidConfiguration(
                "Target language could not be determined automatically. Set at least one of 'with_jni', 'with_objc', 'with_python' or 'with_cppcli' options to `True`."
            )
        if self._cppcli_support:
            if self.settings.os != "Windows":
                raise ConanInvalidConfiguration(
                    "C++/CLI has been enabled on a non-Windows operating system. This is not supported."
                )
            if self.options.shared:
                raise ConanInvalidConfiguration("C++/CLI does not support building as shared library")
            if self.settings.compiler.runtime == "MT" or self.settings.compiler.runtime == "MTd":
                raise ConanInvalidConfiguration("'/clr' and '/MT' command-line options are incompatible")
            if self._objc_support or self._jni_support or self._python_support:
                raise ConanInvalidConfiguration(
                    "C++/CLI is not yet supported with other languages enabled as well. Disable 'with_jni', 'with_objc' and 'with_python' options for a valid configuration."
                )
        if self._python_support:
            if self.settings.os == "Windows":
                raise ConanInvalidConfiguration(
                    "Python on Windows is not fully yet supported, please see https://github.com/cross-language-cpp/djinni-support-lib/issues."
                )
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, "17")
        try:
            minimum_required_compiler_version = self._supported_compilers[str(self.settings.compiler)]
            if Version(self.settings.compiler.version) < minimum_required_compiler_version:
                raise ConanInvalidConfiguration(
                    "This package requires c++17 support. The current compiler does not support it."
                )
        except KeyError:
            self.output.warn(
                "This recipe has no support for the current compiler. Please consider adding it."
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        tc.variables["DJINNI_WITH_OBJC"] = self._objc_support
        tc.variables["DJINNI_WITH_JNI"] = self._jni_support
        tc.variables["DJINNI_WITH_PYTHON"] = self._python_support
        tc.variables["DJINNI_WITH_CPPCLI"] = self._cppcli_support
        tc.variables["BUILD_TESTING"] = False
        if self._jni_support:
            tc.variables["JAVA_AWT_LIBRARY"] = "NotNeeded"
            tc.variables["JAVA_AWT_INCLUDE_PATH"] = "NotNeeded"
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
