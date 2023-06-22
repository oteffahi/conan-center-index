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
import contextlib
import functools
import os

required_conan_version = ">=1.33.0"


class SwigConan(ConanFile):
    name = "swig"
    description = "SWIG is a software development tool that connects programs written in C and C++ with a variety of high-level programming languages."
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://www.swig.org"
    license = "GPL-3.0-or-later"
    topics = ("python", "java", "wrapper")
    exports_sources = "patches/**", "cmake/*"
    settings = "os", "arch", "compiler", "build_type"

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    @property
    def _use_pcre2(self):
        return self.version not in ["4.0.1", "4.0.2"]

    def requirements(self):
        if self._use_pcre2:
            self.requires("pcre2/10.40")
        else:
            self.requires("pcre/8.45")

    def build_requirements(self):
        if self._settings_build.os == "Windows" and not get_env(self, "CONAN_BASH_PATH"):
            self.build_requires("msys2/cci.latest")
        if self.settings.compiler == "Visual Studio":
            self.build_requires("winflexbison/2.5.24")
        else:
            self.build_requires("bison/3.8.2")
        self.build_requires("automake/1.16.5")

    def package_id(self):
        del self.info.settings.compiler

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @property
    def _user_info_build(self):
        # If using the experimental feature with different context for host and
        # build, the 'user_info' attributes of the 'build_requires' packages
        # will be located into the 'user_info_build' object. In other cases they
        # will be located into the 'deps_user_info' object.
        return getattr(self, "user_info_build", self.deps_user_info)

    @contextlib.contextmanager
    def _build_context(self):
        env = {}
        if self.settings.compiler != "Visual Studio":
            env["YACC"] = self._user_info_build["bison"].YACC
        if self.settings.compiler == "Visual Studio":
            with vcvars(self):
                env.update(
                    {
                        "CC": "{} cl -nologo".format(unix_path(self._user_info_build["automake"].compile)),
                        "CXX": "{} cl -nologo".format(unix_path(self._user_info_build["automake"].compile)),
                        "AR": "{} link".format(self._user_info_build["automake"].ar_lib),
                        "LD": "link",
                    }
                )
                with environment_append(self, env):
                    yield
        else:
            with environment_append(self, env):
                yield

    @functools.lru_cache(1)
    def _configure_autotools(self):
        autotools = AutoToolsBuildEnvironment(self, win_bash=tools.os_info.is_windows)
        deps_libpaths = autotools.library_paths
        deps_libs = autotools.libs
        deps_defines = autotools.defines
        if self.settings.os == "Windows" and self.settings.compiler != "Visual Studio":
            autotools.link_flags.append("-static")

        libargs = list('-L"{}"'.format(p) for p in deps_libpaths) + list(
            '-l"{}"'.format(l) for l in deps_libs
        )
        args = [
            "{}_LIBS={}".format("PCRE2" if self._use_pcre2 else "PCRE", " ".join(libargs)),
            "{}_CPPFLAGS={}".format(
                "PCRE2" if self._use_pcre2 else "PCRE",
                " ".join("-D{}".format(define) for define in deps_defines),
            ),
            "--host={}".format(self.settings.arch),
            "--with-swiglibdir={}".format(self._swiglibdir),
        ]
        if self.settings.os == "Linux":
            args.append("LIBS=-ldl")

        host, build = None, None

        if self.settings.compiler == "Visual Studio":
            self.output.warn("Visual Studio compiler cannot create ccache-swig. Disabling ccache-swig.")
            args.append("--disable-ccache")
            autotools.flags.append("-FS")
            # MSVC canonical names aren't understood
            host, build = False, False

        if self.settings.os == "Macos" and self.settings.arch == "armv8":
            # FIXME: Apple ARM should be handled by build helpers
            autotools.flags.append("-arch arm64")
            autotools.link_flags.append("-arch arm64")

        autotools.libs = []
        autotools.library_paths = []

        if self.settings.os == "Windows" and self.settings.compiler != "Visual Studio":
            autotools.libs.extend(["mingwex", "ssp"])

        autotools.configure(args=args, configure_dir=self.source_folder, host=host, build=build)
        return autotools

    def _patch_sources(self):
        apply_conandata_patches(self)

    def build(self):
        self._patch_sources()
        with chdir(self, os.path.join(self.source_folder)):
            self.run("./autogen.sh", win_bash=tools.os_info.is_windows)
        with self._build_context():
            autotools = self._configure_autotools()
            autotools.make()

    def package(self):
        copy(self, pattern="LICENSE*", dst="licenses", src=self.source_folder)
        copy(self, pattern="COPYRIGHT", dst="licenses", src=self.source_folder)
        copy(self, "*", src="cmake", dst=self._module_subfolder)
        with self._build_context():
            autotools = self._configure_autotools()
            autotools.install()

    @property
    def _swiglibdir(self):
        return os.path.join(self.package_folder, "bin", "swiglib").replace("\\", "/")

    @property
    def _module_subfolder(self):
        return os.path.join("lib", "cmake")

    @property
    def _module_file(self):
        return "conan-official-{}-targets.cmake".format(self.name)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.names["cmake_find_package"] = "SWIG"
        self.cpp_info.names["cmake_find_package_multi"] = "SWIG"
        self.cpp_info.builddirs = [self._module_subfolder]
        self.cpp_info.build_modules["cmake_find_package"] = [
            os.path.join(self._module_subfolder, self._module_file)
        ]
        self.cpp_info.build_modules["cmake_find_package_multi"] = [
            os.path.join(self._module_subfolder, self._module_file)
        ]

        bindir = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH environment variable: {}".format(bindir))
        self.env_info.PATH.append(bindir)
