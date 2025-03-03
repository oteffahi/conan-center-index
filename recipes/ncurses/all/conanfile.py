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
import functools
import os
import textwrap

required_conan_version = ">=1.53.0"


class NCursesConan(ConanFile):
    name = "ncurses"
    description = (
        "The ncurses (new curses) library is a free software emulation of curses in System V Release 4.0"
        " (SVr4), and more"
    )
    license = "X11"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.gnu.org/software/ncurses"
    topics = ("terminal", "screen", "tui")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_widec": [True, False],
        "with_extended_colors": [True, False],
        "with_cxx": [True, False],
        "with_progs": [True, False],
        "with_ticlib": ["auto", True, False],
        "with_reentrant": [True, False],
        "with_tinfo": ["auto", True, False],
        "with_pcre2": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_widec": True,
        "with_extended_colors": True,
        "with_cxx": True,
        "with_progs": True,
        "with_ticlib": "auto",
        "with_reentrant": False,
        "with_tinfo": "auto",
        "with_pcre2": False,
    }

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    @property
    def _with_ticlib(self):
        if self.options.with_ticlib == "auto":
            return self.settings.os != "Windows"
        else:
            return self.options.with_ticlib

    @property
    def _with_tinfo(self):
        if self.options.with_tinfo == "auto":
            return self.settings.os != "Windows"
        else:
            return self.options.with_tinfo

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        if not self.options.with_cxx:
            self.settings.rm_safe("compiler.libcxx")
            self.settings.rm_safe("compiler.cppstd")
        if not self.options.with_widec:
            self.options.rm_safe("with_extended_colors")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        if self.options.with_pcre2:
            self.requires("pcre2/10.42")
        if is_msvc(self):
            self.requires("getopt-for-visual-studio/20200201")
            self.requires("dirent/1.23.2")
            if self.options.get_safe("with_extended_colors", False):
                self.requires("naive-tsearch/0.1.1")

    @property
    def _suffix(self):
        res = ""
        if self.options.with_reentrant:
            res += "t"
        if self.options.with_widec:
            res += "w"
        return res

    @property
    def _lib_suffix(self):
        res = self._suffix
        if self.options.shared:
            if self.settings.os == "Windows":
                res += ".dll"
        return res

    def package_id(self):
        self.info.options.with_ticlib = self._with_ticlib
        self.info.options.with_tinfo = self._with_tinfo

    def validate(self):
        if any("arm" in arch for arch in (self.settings.arch, self._settings_build.arch)) and cross_building(self):
            # FIXME: Cannot build ncurses from x86_64 to armv8 (Apple M1).  Cross building from Linux/x86_64 to Mingw/x86_64 works flawless.
            # FIXME: Need access to environment of build profile to set build compiler (BUILD_CC/CC_FOR_BUILD)
            raise ConanInvalidConfiguration("Cross building to/from arm is (currently) not supported")
        if self.options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration("Cannot build shared libraries with static (MT) runtime")
        if self.settings.os == "Windows":
            if self._with_tinfo:
                raise ConanInvalidConfiguration(
                    "terminfo cannot be built on Windows because it requires a term driver"
                )
            if self.options.shared and self._with_ticlib:
                raise ConanInvalidConfiguration(
                    "ticlib cannot be built separately as a shared library on Windows"
                )

    def build_requirements(self):
        if self._settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        yes_no = lambda v: "yes" if v else "no"
        tc.configure_args += [
            "--with-shared={}".format(yes_no(self.options.shared)),
            "--with-cxx-shared={}".format(yes_no(self.options.shared)),
            "--with-normal={}".format(yes_no(not self.options.shared)),
            "--enable-widec={}".format(yes_no(self.options.with_widec)),
            "--enable-ext-colors={}".format(yes_no(self.options.get_safe("with_extended_colors", False))),
            "--enable-reentrant={}".format(yes_no(self.options.with_reentrant)),
            "--with-pcre2={}".format(yes_no(self.options.with_pcre2)),
            "--with-cxx-binding={}".format(yes_no(self.options.with_cxx)),
            "--with-progs={}".format(yes_no(self.options.with_progs)),
            "--with-termlib={}".format(yes_no(self._with_tinfo)),
            "--with-ticlib={}".format(yes_no(self._with_ticlib)),
            "--without-libtool",
            "--without-ada",
            "--without-manpages",
            "--without-tests",
            "--disable-echo",
            "--without-debug",
            "--without-profile",
            "--with-sp-funcs",
            "--disable-rpath",
            "--datarootdir={}".format(unix_path(self, os.path.join(self.package_folder, "res"))),
            "--disable-pc-files",
        ]
        build = None
        host = None
        if self.settings.os == "Windows":
            tc.configure_args += [
                    "--disable-macros",
                    "--disable-termcap",
                    "--enable-database",
                    "--enable-sp-funcs",
                    "--enable-term-driver",
                    "--enable-interop",
                ]
        if is_msvc(self):
            build = host = "{}-w64-mingw32-msvc".format(self.settings.arch)
            tc.configure_args.extend(["ac_cv_func_getopt=yes", "ac_cv_func_setvbuf_reversed=no"])
            tc.cxxflags.append("-EHsc")
            if Version(self.settings.compiler.version) >= 12:
                tc.cxxflags.append("-FS")
        if (self.settings.os, self.settings.compiler) == ("Windows", "gcc"):
            # add libssp (gcc support library) for some missing symbols (e.g. __strcpy_chk)
            tc.libs.extend(["mingwex", "ssp"])
        if build:
            tc.configure_args.append(f"ac_cv_build={build}")
        if host:
            tc.configure_args.append(f"ac_cv_host={host}")
            tc.configure_args.append(f"ac_cv_target={host}")
        tc.generate()

        tc = PkgConfigDeps(self)
        tc.generate()

        if is_msvc(self):
            env = Environment()
            automake_conf = self.dependencies.build["automake"].conf_info
            compile_wrapper = unix_path(self, automake_conf.get("user.automake:compile-wrapper", check_type=str))
            ar_wrapper = unix_path(self, automake_conf.get("user.automake:lib-wrapper", check_type=str))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f'{ar_wrapper} "lib -nologo"')
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
            env.vars(self).save_script("conanbuild_msvc")

    def _patch_sources(self):
        apply_conandata_patches(self)

    def build(self):
        self._patch_sources()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

    @property
    def _major_version(self):
        return Version(self.version).major

    def _create_cmake_module_alias_targets(self, module_file):
        save(
            self,
            module_file,
            textwrap.dedent("""\
            set(CURSES_FOUND ON)
            set(CURSES_INCLUDE_DIRS ${ncurses_libcurses_INCLUDE_DIRS})
            set(CURSES_LIBRARIES ${ncurses_libcurses_LINK_LIBS})
            set(CURSES_CFLAGS ${ncurses_DEFINITIONS} ${ncurses_COMPILE_OPTIONS_C})
            set(CURSES_HAVE_CURSES_H OFF)
            set(CURSES_HAVE_NCURSES_H OFF)
            if(CURSES_NEED_NCURSES)
                set(CURSES_HAVE_NCURSES_CURSES_H ON)
                set(CURSES_HAVE_NCURSES_NCURSES_H ON)
            endif()

            # Backward Compatibility
            set(CURSES_INCLUDE_DIR ${CURSES_INCLUDE_DIRS})
            set(CURSES_LIBRARY ${CURSES_LIBRARIES})
        """),
        )

    def package(self):
        # return
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

        os.unlink(
            os.path.join(self.package_folder, "bin", f"ncurses{self._suffix}{self._major_version}-config")
        )

        self._create_cmake_module_alias_targets(
            os.path.join(self.package_folder, self._module_subfolder, self._module_file)
        )

    @property
    def _module_subfolder(self):
        return os.path.join("lib", "cmake")

    @property
    def _module_file(self):
        return "conan-official-{}-targets.cmake".format(self.name)

    def package_info(self):
        self.cpp_info.filenames["cmake_find_package"] = "Curses"
        self.cpp_info.filenames["cmake_find_package_multi"] = "Curses"
        if self._with_tinfo:
            self.cpp_info.components["tinfo"].libs = ["tinfo" + self._lib_suffix]
            self.cpp_info.components["tinfo"].set_property("pkg_config_name", "tinfo" + self._lib_suffix)
            self.cpp_info.components["tinfo"].includedirs.append(
                os.path.join("include", "ncurses" + self._suffix)
            )

        self.cpp_info.components["libcurses"].libs = ["ncurses" + self._lib_suffix]
        self.cpp_info.components["libcurses"].set_property("pkg_config_name", "ncurses" + self._lib_suffix)
        self.cpp_info.components["libcurses"].includedirs.append(
            os.path.join("include", "ncurses" + self._suffix)
        )
        if not self.options.shared:
            self.cpp_info.components["libcurses"].defines = ["NCURSES_STATIC"]
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components["libcurses"].system_libs = ["dl", "m"]
        if self._with_tinfo:
            self.cpp_info.components["libcurses"].requires.append("tinfo")

        if is_msvc(self):
            self.cpp_info.components["libcurses"].requires.extend(
                ["getopt-for-visual-studio::getopt-for-visual-studio", "dirent::dirent"]
            )
            if self.options.get_safe("with_extended_colors", False):
                self.cpp_info.components["libcurses"].requires.append("naive-tsearch::naive-tsearch")

        module_rel_path = os.path.join(self._module_subfolder, self._module_file)
        self.cpp_info.components["libcurses"].builddirs.append(self._module_subfolder)
        self.cpp_info.components["libcurses"].build_modules["cmake_find_package"] = [module_rel_path]
        self.cpp_info.components["libcurses"].build_modules["cmake_find_package_multi"] = [module_rel_path]

        self.cpp_info.components["panel"].libs = ["panel" + self._lib_suffix]
        self.cpp_info.components["panel"].set_property("pkg_config_name", "panel" + self._lib_suffix)
        self.cpp_info.components["panel"].requires = ["libcurses"]

        self.cpp_info.components["menu"].libs = ["menu" + self._lib_suffix]
        self.cpp_info.components["menu"].set_property("pkg_config_name", "menu" + self._lib_suffix)
        self.cpp_info.components["menu"].requires = ["libcurses"]

        self.cpp_info.components["form"].libs = ["form" + self._lib_suffix]
        self.cpp_info.components["form"].set_property("pkg_config_name", "form" + self._lib_suffix)
        self.cpp_info.components["form"].requires = ["libcurses"]
        if self.options.with_pcre2:
            self.cpp_info.components["form"].requires.append("pcre2::pcre2")

        if self.options.with_cxx:
            self.cpp_info.components["curses++"].libs = ["ncurses++" + self._lib_suffix]
            self.cpp_info.components["curses++"].set_property(
                "pkg_config_name", "ncurses++" + self._lib_suffix
            )
            self.cpp_info.components["curses++"].requires = ["libcurses"]

        if self._with_ticlib:
            self.cpp_info.components["ticlib"].libs = ["tic" + self._lib_suffix]
            self.cpp_info.components["ticlib"].set_property("pkg_config_name", "tic" + self._lib_suffix)
            self.cpp_info.components["ticlib"].requires = ["libcurses"]

        if self.options.with_progs:
            bin_path = os.path.join(self.package_folder, "bin")
            self.output.info(f"Appending PATH environment variable: {bin_path}")
            self.env_info.PATH.append(bin_path)

        terminfo = os.path.join(self.package_folder, "res", "terminfo")
        self.output.info("Setting TERMINFO environment variable: {}".format(terminfo))
        self.env_info.TERMINFO = terminfo

        self.conf_info.define("user.ncurses:lib_suffix", self._lib_suffix)
        self.user_info.lib_suffix = self._lib_suffix
