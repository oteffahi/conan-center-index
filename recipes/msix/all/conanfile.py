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

required_conan_version = ">=1.33.0"


class MsixConan(ConanFile):
    name = "msix"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/microsoft/msix-packaging"
    description = "An SDK for creating MSIX packages"
    topics = ("sdk", "packaging", "conan-recipe")

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "crypto_lib": ["crypt32", "openssl"],
        "pack": [True, False],
        "skip_bundles": [True, False],
        "use_external_zlib": [True, False],
        "use_validation_parser": [True, False],
        "xml_parser": ["applexml", "javaxml", "msxml6", "xerces"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "crypto_lib": "openssl",
        "pack": False,
        "skip_bundles": False,
        "use_external_zlib": True,
        "use_validation_parser": False,
        "xml_parser": "msxml6",
    }

    @property
    def _minimum_compilers_version(self):
        return {
            "Visual Studio": "15",
        }

    def export_sources(self):
        export_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "Android":
            tc.variables["AOSP"] = True
        if self.settings.os == "Linux":
            tc.variables["LINUX"] = True
        if self.settings.os == "Macos":
            tc.variables["MACOS"] = True
        tc.variables["CRYPTO_LIB"] = self.options.crypto_lib
        tc.variables["MSIX_PACK"] = self.options.pack
        tc.variables["MSIX_SAMPLES"] = False
        tc.variables["MSIX_TESTS"] = False
        tc.variables["SKIP_BUNDLES"] = self.options.skip_bundles
        tc.variables["USE_MSIX_SDK_ZLIB"] = self.options.use_external_zlib
        tc.variables["USE_SHARED_ZLIB"] = self.options["zlib"].shared
        tc.variables["USE_VALIDATION_PARSER"] = self.options.use_validation_parser
        tc.variables["XML_PARSER"] = self.options.xml_parser
        tc.variables["CALCULATE_VERSION"] = False
        tc.variables["ENABLE_NUGET_PACKAGING"] = False
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def _validate_compiler_settings(self):
        compiler = self.settings.compiler
        if compiler.get_safe("cppstd"):
            check_min_cppstd(self, "17")

        min_version = self._minimum_compilers_version.get(str(self.settings.compiler))
        if not min_version:
            self.output.warn(
                "{} recipe lacks information about the {} compiler support.".format(
                    self.name, self.settings.compiler
                )
            )
        elif Version(self.settings.compiler.version) < min_version:
            raise ConanInvalidConfiguration(
                "{} requires C++17 support. The current compiler {} {} does not support it.".format(
                    self.name, self.settings.compiler, self.settings.compiler.version
                )
            )

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
            self.options.crypto_lib = "crypt32"

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        if self.settings.os == "Linux" and not self.options.skip_bundles:
            self.requires("icu/71.1")
        if self.options.crypto_lib == "openssl":
            self.requires("openssl/1.1.1q")
        if self.options.use_external_zlib:
            self.requires("zlib/1.2.12")
        if self.options.xml_parser == "xerces":
            self.requires("xerces-c/3.2.3")

    def validate(self):
        if self.settings.os != "Android" and self.options.xml_parser == "javaxml":
            raise ConanInvalidConfiguration("javaxml is supported only for Android")
        if self.settings.os == "Linux" and self.settings.compiler != "clang":
            raise ConanInvalidConfiguration("Only clang is supported on Linux")
        if self.settings.os != "Macos" and self.options.xml_parser == "applexml":
            raise ConanInvalidConfiguration("applexml is supported only for MacOS")
        if self.settings.os != "Windows" and self.options.crypto_lib == "crypt32":
            raise ConanInvalidConfiguration("crypt32 is supported only for Windows")
        if self.settings.os != "Windows" and self.options.xml_parser == "msxml6":
            raise ConanInvalidConfiguration("msxml6 is supported only for Windows")
        if self.options.pack:
            if self.settings.os == "Macos":
                if not self.options.use_external_zlib:
                    raise ConanInvalidConfiguration(
                        "Using libCompression APIs and packaging features is not supported"
                    )
                if self.options.xml_parser != "xerces":
                    raise ConanInvalidConfiguration("Xerces is the only supported parser for MacOS pack")
            if not self.options.use_validation_parser:
                raise ConanInvalidConfiguration("Packaging requires validation parser")
        if self.options.xml_parser == "xerces" and self.options["xerces-c"].char_type != "char16_t":
            raise ConanInvalidConfiguration("Only char16_t is supported for xerces-c")

        self._validate_compiler_settings()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["runtimeobject"]
            if self.settings.compiler == "Visual Studio":
                self.cpp_info.system_libs.append("delayimp")
            if self.options.crypto_lib == "crypt32":
                self.cpp_info.system_libs.extend(["bcrypt", "crypt32", "wintrust"])
            if self.options.xml_parser == "msxml6":
                self.cpp_info.system_libs.append("msxml6")
