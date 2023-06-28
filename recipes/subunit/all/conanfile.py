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
import contextlib
import glob
import os

required_conan_version = ">=1.53.0"


class SubunitConan(ConanFile):
    name = "subunit"
    description = "A streaming protocol for test results"
    license = ("Apache-2.0", "BSD-3-Clause")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://launchpad.net/subunit"
    topics = ("subunit", "streaming", "protocol", "test", "results")

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

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cppunit/1.15.1")

    def validate(self):
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration("Cannot build shared subunit libraries on Windows")
        if self.settings.compiler == "apple-clang" and Version(self.settings.compiler.version) < "10":
            # Complete error is:
            # make[2]: *** No rule to make target `/Applications/Xcode-9.4.app/Contents/Developer/Platforms/MacOSX.platform/Developer/SDKs/MacOSX10.13.sdk/System/Library/Perl/5.18/darwin-thread-multi-2level/CORE/config.h', needed by `Makefile'.  Stop.
            raise ConanInvalidConfiguration(
                "Due to weird make error involving missing config.h file in sysroot"
            )

    def build_requirements(self):
        if self._settings_build.os == "Windows" and not get_env(self, "CONAN_BASH_PATH"):
            self.build_requires("msys2/cci.latest")
        if is_msvc(self):
            self.build_requires("automake/1.16.3")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # TODO: fill in generate()
        pass

    @contextlib.contextmanager
    def _build_context(self):
        if is_msvc(self):
            with vcvars(self):
                env = {
                    "AR": "{} lib".format(unix_path(self, self.conf_info.get("user.automake:ar_lib"))),
                    "CC": "{} cl -nologo".format(unix_path(self, self.conf_info.get("user.automake:compile"))),
                    "CXX": "{} cl -nologo".format(unix_path(self, self.conf_info.get("user.automake:compile"))),
                    "NM": "dumpbin -symbols",
                    "OBJDUMP": ":",
                    "RANLIB": ":",
                    "STRIP": ":",
                }
                with environment_append(self, env):
                    yield
        else:
            yield

    def _configure_autotools(self):
        tc = AutotoolsToolchain(self)
        if is_msvc(self):
            tc.cxxflags.append("-FS")
            tc.cxxflags.append("-EHsc")
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args = [
            "CHECK_CFLAGS=' '",
            "CHECK_LIBS=' '",
            "CPPUNIT_CFLAGS='{}'".format(
                " ".join(f"-I{inc}" for inc in self.dependencies["cppunit"].cpp_info.includedirs).replace(
                    "\\", "/"
                )
            ),
            "CPPUNIT_LIBS='{}'".format(" ".join(self.dependencies["cppunit"].cpp_info.libs)),
        ]
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        with self._build_context():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        with self._build_context():
            autotools = Autotools(self)
            autotools.configure()
            # Avoid installing i18n + perl things in arch-dependent folders or in a `local` subfolder
            install_args = [
                "INSTALLARCHLIB={}".format(os.path.join(self.package_folder, "lib").replace("\\", "/")),
                "INSTALLSITEARCH={}".format(os.path.join(self.build_folder, "archlib").replace("\\", "/")),
                "INSTALLVENDORARCH={}".format(os.path.join(self.build_folder, "archlib").replace("\\", "/")),
                "INSTALLSITEBIN={}".format(os.path.join(self.package_folder, "bin").replace("\\", "/")),
                "INSTALLSITESCRIPT={}".format(os.path.join(self.package_folder, "bin").replace("\\", "/")),
                "INSTALLSITEMAN1DIR={}".format(
                    os.path.join(self.build_folder, "share", "man", "man1").replace("\\", "/")
                ),
                "INSTALLSITEMAN3DIR={}".format(
                    os.path.join(self.build_folder, "share", "man", "man3").replace("\\", "/")
                ),
            ]
            autotools.install(args=install_args)

        rm(self, "*.la", self.package_folder, recursive=True)
        rm(self, "*.pod", os.path.join(self.package_folder, "lib"), recursive=True)
        for d in glob.glob(os.path.join(self.package_folder, "lib", "python*")):
            rmdir(self, d)
        for d in glob.glob(os.path.join(self.package_folder, "lib", "*")):
            if os.path.isdir(d):
                rmdir(self, d)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "Library"))

    def package_info(self):
        self.cpp_info.components["libsubunit"].libs = ["subunit"]
        self.cpp_info.components["libsubunit"].names["pkgconfig"] = "libsubunit"
        self.cpp_info.components["libcppunit_subunit"].libs = ["cppunit_subunit"]
        self.cpp_info.components["libcppunit_subunit"].requires = ["cppunit::cppunit"]
        self.cpp_info.components["libcppunit_subunit"].names["pkgconfig"] = "libcppunit_subunit"

        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.env_info.PATH.append(bin_path)
