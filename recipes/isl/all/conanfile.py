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
from contextlib import contextmanager
import os

required_conan_version = ">=1.33.0"


class IslConan(ConanFile):
    name = "isl"
    description = "isl is a library for manipulating sets and relations of integer points bounded by linear constraints."
    topics = ("integer", "set", "library")
    license = "MIT"
    homepage = "https://libisl.sourceforge.io"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False], "with_int": ["gmp", "imath", "imath-32"]}
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_int": "gmp",
    }

    _autotools = None

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            del self.options.fPIC
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

    def validate(self):
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration(
                "Cannot build shared isl library on Windows (due to libtool refusing to link to static/import libraries)"
            )
        if self.settings.os == "Macos" and self.settings.arch == "armv8":
            raise ConanInvalidConfiguration("Apple M1 is not yet supported. Contributions are welcome")
        if self.options.with_int != "gmp":
            # FIXME: missing imath recipe
            raise ConanInvalidConfiguration("imath is not (yet) available on cci")
        if (
            self.settings.compiler == "Visual Studio"
            and tools.Version(self.settings.compiler.version) < 16
            and self.settings.compiler.runtime == "MDd"
        ):
            # gmp.lib(bdiv_dbm1c.obj) : fatal error LNK1318: Unexpected PDB error; OK (0)
            raise ConanInvalidConfiguration(
                "isl fails to link with this version of visual studio and MDd runtime"
            )

    def requirements(self):
        if self.options.with_int == "gmp":
            self.requires("gmp/6.2.1")

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def build_requirements(self):
        if self._settings_build.os == "Windows" and not tools.get_env("CONAN_BASH_PATH"):
            self.build_requires("msys2/cci.latest")
        if self.settings.compiler == "Visual Studio":
            self.build_requires("automake/1.16.4")

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder
        )

    @contextmanager
    def _build_context(self):
        if self.settings.compiler == "Visual Studio":
            with tools.vcvars(self.settings):
                env = {
                    "AR": "{} lib".format(tools.unix_path(self.deps_user_info["automake"].ar_lib)),
                    "CC": "{} cl -nologo -{}".format(
                        tools.unix_path(self.deps_user_info["automake"].compile),
                        self.settings.compiler.runtime,
                    ),
                    "CXX": "{} cl -nologo -{}".format(
                        tools.unix_path(self.deps_user_info["automake"].compile),
                        self.settings.compiler.runtime,
                    ),
                    "NM": "dumpbin -symbols",
                    "OBJDUMP": ":",
                    "RANLIB": ":",
                    "STRIP": ":",
                }
                with tools.environment_append(env):
                    yield
        else:
            yield

    def _configure_autotools(self):
        if self._autotools:
            return self._autotools
        self._autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
        self._autotools.libs = []
        yes_no = lambda v: "yes" if v else "no"
        conf_args = [
            "--with-int={}".format(self.options.with_int),
            "--enable-portable-binary",
            "--enable-shared={}".format(yes_no(self.options.shared)),
            "--enable-static={}".format(yes_no(not self.options.shared)),
        ]
        if self.options.with_int == "gmp":
            conf_args.extend(
                [
                    "--with-gmp=system",
                    "--with-gmp-prefix={}".format(self.deps_cpp_info["gmp"].rootpath.replace("\\", "/")),
                ]
            )
        if self.settings.compiler == "Visual Studio":
            if tools.Version(self.settings.compiler.version) >= 15:
                self._autotools.flags.append("-Zf")
            if tools.Version(self.settings.compiler.version) >= 12:
                self._autotools.flags.append("-FS")
        self._autotools.configure(args=conf_args, configure_dir=self._source_subfolder)
        return self._autotools

    def build(self):
        with self._build_context():
            autotools = self._configure_autotools()
            autotools.make()

    def package(self):
        self.copy("LICENSE", src=self._source_subfolder, dst="licenses")
        with self._build_context():
            autotools = self._configure_autotools()
            autotools.install()

        os.unlink(os.path.join(os.path.join(self.package_folder, "lib", "libisl.la")))
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.names["pkg_config"] = "isl"
        self.cpp_info.libs = ["isl"]
