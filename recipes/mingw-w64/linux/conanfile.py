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

required_conan_version = ">=1.52.0"


class MingwConan(ConanFile):
    name = "mingw-w64"
    description = "MinGW is a contraction of Minimalist GNU for Windows"
    license = ("ZPL-2.1", "MIT", "GPL-2.0-or-later")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.mingw-w64.org/"
    topics = ("gcc", "gnu", "unix", "mingw32", "binutils")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "threads": ["posix", "win32"],
        "exception": ["seh", "sjlj"],
        "gcc": ["10.3.0"],
    }
    default_options = {
        "threads": "posix",
        "exception": "seh",
        "gcc": "10.3.0",
    }
    no_copy_source = True

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        del self.info.settings.compiler
        del self.info.settings.build_type

    def validate(self):
        valid_os = ["Linux"]
        if str(self.settings.os) not in valid_os:
            raise ConanInvalidConfiguration(
                "MinGW {} is only supported for the following operating systems: {}".format(
                    self.version, valid_os
                )
            )
        valid_arch = ["x86_64"]
        if str(self.settings.arch) not in valid_arch:
            raise ConanInvalidConfiguration(
                "MinGW {} is only supported for the following architectures on {}: {}".format(
                    self.version, str(self.settings.os), valid_arch
                )
            )

        if "gcc" in self.conan_data["sources"][self.version]:
            valid_gcc = self.conan_data["sources"][self.version]["gcc"].keys()
            if str(self.options.gcc) not in valid_gcc:
                raise ConanInvalidConfiguration(
                    "gcc version {} is not in the list of valid versions: {}".format(
                        str(self.options.gcc), valid_gcc
                    )
                )

    def build_requirements(self):
        self.tool_requires("m4/1.4.19")
        self.tool_requires("gmp/6.3.0")
        self.tool_requires("mpfr/4.2.1")
        self.tool_requires("mpc/1.3.1")

    def _download_source(self):
        arch_data = self.conan_data["sources"][self.version]

        for package in arch_data:
            if package == "gcc":
                continue
            self.output.info("Downloading {} from {}".format(package, arch_data[package]["url"]))
            get(
                self,
                **arch_data[package],
                strip_root=True,
                destination=os.path.join(self.build_folder, "sources", package),
            )
        # Download gcc version
        gcc_data = arch_data["gcc"][str(self.options.gcc)]
        get(self, **gcc_data, strip_root=True, destination=os.path.join(self.build_folder, "sources", "gcc"))

    @property
    def _target_tag(self):
        return "x86_64-w64-mingw32"

    def build(self):
        # Source should be downloaded in the build step since it depends on specific options
        self._download_source()

        target_tag = self._target_tag
        host_tag = "x86_64-linux-gnu"

        # We currently cannot build with multilib and threads=posix. Otherwise we get the gcc compile error:
        # checking for ld that supports -Wl,--gc-sections... configure: error: Link tests are not allowed after GCC_NO_EXECUTABLES.
        # Makefile:11275: recipe for target 'configure-target-libstdc++-v3' failed
        build_multilib = False

        # Instructions see:
        # https://sourceforge.net/p/mingw-w64/code/HEAD/tree/trunk/mingw-w64-doc/howto-build/mingw-w64-howto-build.txt
        # and
        # https://sourceforge.net/p/mingw-w64/code/HEAD/tree/trunk/mingw-w64-doc/howto-build/mingw-w64-howto-build-adv.txt
        # also good to see specific commands:
        # https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/host/x86_64-w64-mingw32-4.8/+/lollipop-dev/build-mingw64-toolchain.sh

        # add binutils to path. Required for gcc build
        env = {"PATH": os.environ["PATH"] + ":" + os.path.join(self.package_folder, "bin")}

        with environment_append(self, env):
            with_gmp_mpfc_mpc = [
                "--with-gmp={}".format(self.dependencies["gmp"].package_folder.replace("\\", "/")),
                "--with-mpfr={}".format(self.dependencies["mpfr"].package_folder.replace("\\", "/")),
                "--with-mpc={}".format(self.dependencies["mpc"].package_folder.replace("\\", "/")),
            ]

            self.output.info("Building binutils ...")
            mkdir(self, os.path.join(self.build_folder, "binutils"))
            with chdir(self, os.path.join(self.build_folder, "binutils")):
                tc = AutotoolsToolchain(self)
                tc.configure_args += [
                    "--enable-silent-rules",
                    "--with-sysroot={}".format(self.package_folder),
                    "--disable-nls",
                    "--disable-shared",
                ]
                if build_multilib:
                    tc.configure_args.append("--enable-targets=x86_64-w64-mingw32,i686-w64-mingw32")
                tc.configure_args.extend(with_gmp_mpfc_mpc)
                tc.generate()
                autotools = Autotools(self)
                autotools.make()
                autotools.install()

            self.output.info("Building mingw-w64-tools ...")
            mkdir(self, os.path.join(self.build_folder, "mingw-w64-tools"))
            with chdir(self, os.path.join(self.build_folder, "mingw-w64-tools")):
                autotools = AutoToolsBuildEnvironment(self)
                autotools.configure(
                    configure_dir=os.path.join(
                        self.build_folder, "sources", "mingw-w64", "mingw-w64-tools", "widl"
                    ),
                    args=tc.configure_args,
                    target=target_tag,
                    host=False,
                    build=False,
                )
                autotools.make()
                autotools.install()

            self.output.info("Building mingw-w64-headers ...")
            mkdir(self, os.path.join(self.build_folder, "mingw-w64-headers"))
            with chdir(self, os.path.join(self.build_folder, "mingw-w64-headers")):
                autotools = AutoToolsBuildEnvironment(self)
                tc.configure_args = [
                    "--enable-silent-rules",
                    "--with-widl={}".format(os.path.join(self.package_folder, "bin")),
                    "--enable-sdk=all",
                    "--prefix={}".format(os.path.join(self.package_folder, target_tag)),
                ]
                autotools.configure(
                    configure_dir=os.path.join(
                        self.build_folder, "sources", "mingw-w64", "mingw-w64-headers"
                    ),
                    args=tc.configure_args,
                    target=False,
                    host=target_tag,
                    build=host_tag,
                )
                autotools.make()
                autotools.install()
                # Step 3) GCC requires the x86_64-w64-mingw32 directory be mirrored as a
                # directory 'mingw' in the same root.  So, if using configure default
                # /usr/local, type:
                #     ln -s /usr/local/x86_64-w64-mingw32 /usr/local/mingw
                #     or, for sysroot, type:
                #     ln -s /mypath/x86_64-w64-mingw32 /mypath/mingw
                self.run(
                    "ln -s {} {}".format(
                        os.path.join(self.package_folder, target_tag),
                        os.path.join(self.package_folder, "mingw"),
                    )
                )
                # Step 5) Symlink x86_64-w64-mingw32/lib directory as x86_64-w64-mingw32/lib64:
                # ln -s /usr/local/x86_64-w64-mingw32/lib /usr/local/x86_64-w64-mingw32/lib64
                # or, for sysroot:
                #     ln -s /mypath/x86_64-w64-mingw32/lib /mypath/x86_64-w64-mingw32/lib64
                self.run(
                    "ln -s {} {}".format(
                        os.path.join(self.package_folder, target_tag, "lib"),
                        os.path.join(self.package_folder, target_tag, "lib64"),
                    )
                )

            self.output.info("Building core gcc ...")
            mkdir(self, os.path.join(self.build_folder, "gcc"))
            with chdir(self, os.path.join(self.build_folder, "gcc")):
                autotools_gcc = AutoToolsBuildEnvironment(self)
                tc.configure_args += [
                    "--enable-silent-rules",
                    "--enable-languages=c,c++",
                    "--with-sysroot={}".format(self.package_folder),
                    "--disable-shared",
                ]
                if build_multilib:
                    tc.configure_args.append("--enable-targets=all")
                    tc.configure_args.append("--enable-multilib")
                else:
                    tc.configure_args.append("--disable-multilib")
                tc.configure_args.extend(with_gmp_mpfc_mpc)
                if self.options.exception == "sjlj":
                    tc.configure_args.append("--enable-sjlj-exceptions")
                if self.options.threads == "posix":
                    # Some specific options which need to be set for posix thread. Otherwise it fails compiling.
                    tc.configure_args.extend(
                        [
                            "--enable-silent-rules",
                            "--enable-threads=posix",
                            # Not 100% sure why, but the following options are required, otherwise
                            # gcc fails to build with posix threads
                        ]
                    )
                autotools_gcc.libs = []
                autotools_gcc.configure(
                    configure_dir=os.path.join(self.build_folder, "sources", "gcc"),
                    args=tc.configure_args,
                    target=target_tag,
                    host=False,
                    build=False,
                )
                autotools_gcc.make(target="all-gcc")
                autotools_gcc.make(target="install-gcc")

            env_compiler = dict(env)
            # The CC and CXX compiler must be set to the mingw compiler. Conan already sets CC and CXX, therefore we need to overwrite it.
            # If the wrong compiler is used for mingw-w64-crt, then you will get the error
            # configure: Please check if the mingw-w64 header set and the build/host option are set properly.
            env_compiler["CC"] = target_tag + "-gcc"
            env_compiler["CXX"] = target_tag + "-g++"
            with environment_append(self, env_compiler):
                self.output.info("Building mingw-w64-crt ...")
                mkdir(self, os.path.join(self.build_folder, "mingw-w64-crt"))
                with chdir(self, os.path.join(self.build_folder, "mingw-w64-crt")):
                    autotools = AutoToolsBuildEnvironment(self)
                    tc.configure_args += [
                        "--enable-silent-rules",
                        "--prefix={}".format(os.path.join(self.package_folder, target_tag)),
                        "--with-sysroot={}".format(self.package_folder),
                    ]
                    if build_multilib:
                        tc.configure_args.append("--enable-lib32")
                    autotools.configure(
                        configure_dir=os.path.join(
                            self.build_folder, "sources", "mingw-w64", "mingw-w64-crt"
                        ),
                        args=tc.configure_args,
                        target=False,
                        host=target_tag,
                        build=False,
                        use_default_install_dirs=False,
                    )
                    autotools.make()
                    autotools.install()

                if self.options.threads == "posix":
                    self.output.info("Building mingw-w64-libraries-winpthreads ...")
                    mkdir(self, os.path.join(self.build_folder, "mingw-w64-libraries-winpthreads"))
                    with chdir(self, os.path.join(self.build_folder, "mingw-w64-libraries-winpthreads")):
                        autotools = AutoToolsBuildEnvironment(self)
                        tc.configure_args += [
                            "--enable-silent-rules",
                            "--disable-shared",
                            "--prefix={}".format(os.path.join(self.package_folder, target_tag)),
                        ]
                        autotools.configure(
                            configure_dir=os.path.join(
                                self.build_folder,
                                "sources",
                                "mingw-w64",
                                "mingw-w64-libraries",
                                "winpthreads",
                            ),
                            args=tc.configure_args,
                            target=False,
                            host=target_tag,
                            build=False,
                        )
                        autotools.make()
                        autotools.install()

            self.output.info("Building libgcc ...")
            with chdir(self, os.path.join(self.build_folder, "gcc")):
                autotools_gcc.make()
                autotools_gcc.install()

        self.output.info("Building done!")

    def package(self):
        copy(self, "COPYING",
             src=os.path.join(self.build_folder, "sources", "mingw-w64"),
             dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", self.package_folder, recursive=True)
        rmdir(self, os.path.join(self.package_folder, "share", "man"))
        rmdir(self, os.path.join(self.package_folder, "share", "doc"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # replace with relative symlinks so they'll resolve correctly on consumer's machine
        os.unlink(os.path.join(self.package_folder, "mingw"))
        os.unlink(os.path.join(self.package_folder, self._target_tag, "lib64"))
        self.run(
            "ln -s {} {}".format(
                os.path.join(os.curdir, self._target_tag), os.path.join(self.package_folder, "mingw")
            )
        )
        self.run(
            "ln -s {} {}".format(
                os.path.join(os.curdir, "lib"), os.path.join(self.package_folder, self._target_tag, "lib64")
            )
        )

    def package_info(self):
        self.cpp_info.frameworkdirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []
        self.cpp_info.includedirs = []

        if getattr(self, "settings_target", None):
            if self.settings_target.compiler != "gcc":
                raise ConanInvalidConfiguration("Only GCC is allowed as compiler.")
            if str(self.settings_target.compiler.threads) != str(self.options.threads):
                raise ConanInvalidConfiguration(
                    "Build requires 'mingw' provides binaries for gcc "
                    "with threads={}, your profile:host declares "
                    "threads={}, please use the same value for both.".format(
                        self.options.threads, self.settings_target.compiler.threads
                    )
                )
            if str(self.settings_target.compiler.exception) != str(self.options.exception):
                raise ConanInvalidConfiguration(
                    "Build requires 'mingw' provides binaries for gcc "
                    "with exception={}, your profile:host declares "
                    "exception={}, please use the same value for both.".format(
                        self.options.exception, self.settings_target.compiler.exception
                    )
                )

        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info("Appending PATH env var with : {}".format(bin_path))
        self.env_info.PATH.append(bin_path)
        self.env_info.MINGW_HOME = str(self.package_folder)

        prefix = os.path.join(self.package_folder, "bin", self._target_tag + "-")
        self.env_info.CC = prefix + "gcc"
        self.env_info.CXX = prefix + "g++"
        self.env_info.CPP = prefix + "cpp"
        self.env_info.AR = prefix + "ar"
        self.env_info.AS = prefix + "as"
        self.env_info.GDB = prefix + "gdb"
        self.env_info.LD = prefix + "ld"
        self.env_info.NM = prefix + "nm"
        self.env_info.OBJCOPY = prefix + "objcopy"
        self.env_info.OBJDUMP = prefix + "objdump"
        self.env_info.RANLIB = prefix + "ranlib"
        self.env_info.SIZE = prefix + "size"
        self.env_info.STRINGS = prefix + "strings"
        self.env_info.STRIP = prefix + "strip"
        self.env_info.GCOV = prefix + "gcov"
        self.env_info.RC = prefix + "windres"
        self.env_info.DLLTOOL = prefix + "dlltool"
