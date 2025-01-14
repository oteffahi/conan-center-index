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
from conan.tools.files import apply_conandata_patches, get, rename, replace_in_file
from conan.tools.layout import basic_layout
import os
import shutil
import string

required_conan_version = ">=1.53.0"


class JemallocConan(ConanFile):
    name = "jemalloc"
    description = (
        "jemalloc is a general purpose malloc(3) implementation that emphasizes fragmentation avoidance and"
        " scalable concurrency support."
    )
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://jemalloc.net/"
    topics = ("malloc", "free")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "prefix": "ANY",
        "enable_cxx": [True, False],
        "enable_fill": [True, False],
        "enable_xmalloc": [True, False],
        "enable_readlinkat": [True, False],
        "enable_syscall": [True, False],
        "enable_lazy_lock": [True, False],
        "enable_debug_logging": [True, False],
        "enable_initial_exec_tls": [True, False],
        "enable_libdl": [True, False],
        "enable_prof": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "prefix": "",
        "enable_cxx": True,
        "enable_fill": True,
        "enable_xmalloc": False,
        "enable_readlinkat": False,
        "enable_syscall": True,
        "enable_lazy_lock": False,
        "enable_debug_logging": False,
        "enable_initial_exec_tls": True,
        "enable_libdl": True,
        "enable_prof": False,
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
        if not self.options.enable_cxx:
            self.settings.rm_safe("compiler.libcxx")
            self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if (
            self.options.enable_cxx
            and self.settings.compiler.get_safe("libcxx") == "libc++"
            and self.settings.compiler == "clang"
            and Version(self.settings.compiler.version) < "10"
        ):
            raise ConanInvalidConfiguration(
                "clang and libc++ version {} (< 10) is missing a mutex implementation".format(
                    self.settings.compiler.version
                )
            )
        if self.options.shared and is_msvc_static_runtime(self):
            raise ConanInvalidConfiguration(
                "Visual Studio build for shared library with MT runtime is not supported"
            )
        if is_msvc(self) and self.settings.compiler.version != "15":
            # https://github.com/jemalloc/jemalloc/issues/1703
            raise ConanInvalidConfiguration(
                "Only Visual Studio 15 2017 is supported.  Please fix this if other versions are supported"
            )
        if self.settings.build_type not in ("Release", "Debug", None):
            raise ConanInvalidConfiguration("Only Release and Debug build_types are supported")
        if is_msvc(self) and self.settings.arch not in ("x86_64", "x86"):
            raise ConanInvalidConfiguration("Unsupported arch")
        if self.settings.compiler == "clang" and Version(self.settings.compiler.version) <= "3.9":
            raise ConanInvalidConfiguration("Unsupported compiler version")
        if is_apple_os(self) and self.settings.arch not in ("x86_64", "x86"):
            raise ConanInvalidConfiguration("Unsupported arch")

    def build_requirements(self):
        if self._settings_build.os == "Windows" and not self.conf.get(
            "tools.microsoft.bash:path", default=False, check_type=str
        ):
            self.tool_requires("msys2/cci.latest")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args += [
            "--with-jemalloc-prefix={}".format(self.options.prefix),
            "--enable-debug" if self.settings.build_type == "Debug" else "--disable-debug",
            "--enable-cxx" if self.options.enable_cxx else "--disable-cxx",
            "--enable-fill" if self.options.enable_fill else "--disable-fill",
            "--enable-xmalloc" if self.options.enable_cxx else "--disable-xmalloc",
            "--enable-readlinkat" if self.options.enable_readlinkat else "--disable-readlinkat",
            "--enable-syscall" if self.options.enable_syscall else "--disable-syscall",
            "--enable-lazy-lock" if self.options.enable_lazy_lock else "--disable-lazy-lock",
            "--enable-log" if self.options.enable_debug_logging else "--disable-log",
            (
                "--enable-initial-exec-tls"
                if self.options.enable_initial_exec_tls
                else "--disable-initial-exec-tls"
            ),
            "--enable-libdl" if self.options.enable_libdl else "--disable-libdl",
        ]
        if self.options.enable_prof:
            tc.configure_args.append("--enable-prof")
        tc.generate()

    @property
    def _msvc_build_type(self):
        build_type = str(self.settings.build_type) or "Release"
        if not self.options.shared:
            build_type += "-static"
        return build_type

    def _patch_sources(self):
        if self.settings.os == "Windows":
            makefile_in = os.path.join(self.source_folder, "Makefile.in")
            replace_in_file(
                self,
                makefile_in,
                "DSO_LDFLAGS = @DSO_LDFLAGS@",
                "DSO_LDFLAGS = @DSO_LDFLAGS@ -Wl,--out-implib,lib/libjemalloc.a",
                strict=False,
            )
            replace_in_file(
                self,
                makefile_in,
                (
                    "\t$(INSTALL) -d $(LIBDIR)\n"
                    "\t$(INSTALL) -m 755 $(objroot)lib/$(LIBJEMALLOC).$(SOREV) $(LIBDIR)"
                ),
                (
                    "\t$(INSTALL) -d $(BINDIR)\n"
                    "\t$(INSTALL) -d $(LIBDIR)\n"
                    "\t$(INSTALL) -m 755 $(objroot)lib/$(LIBJEMALLOC).$(SOREV) $(BINDIR)\n"
                    "\t$(INSTALL) -m 644 $(objroot)lib/libjemalloc.a $(LIBDIR)"
                ),
                strict=False,
            )

        apply_conandata_patches(self)

    def build(self):
        self._patch_sources()
        if is_msvc(self):
            with tools_legacy.vcvars(self.settings) if is_msvc(self) else tools_legacy.no_op():
                with (
                    tools_legacy.environment_append(
                        {
                            "CC": "cl",
                            "CXX": "cl",
                        }
                    )
                    if is_msvc(self)
                    else tools_legacy.no_op()
                ):
                    with tools_legacy.chdir(self, self.source_folder):
                        # Do not use AutoToolsBuildEnvironment because we want to run configure as ./configure
                        self.run(
                            "./configure {}".format(" ".join(self._autotools_args)),
                            win_bash=tools_legacy.os_info.is_windows,
                        )
            msbuild = MSBuild(self)
            # Do not use the 2015 solution: unresolved external symbols: test_hooks_libc_hook and test_hooks_arena_new_hook
            sln_file = os.path.join(self.source_folder, "msvc", "jemalloc_vc2017.sln")
            msbuild.build(sln_file, targets=["jemalloc"], build_type=self._msvc_build_type)
        else:
            autotools = Autotools()
            autotools.configure()
            autotools.make()

    @property
    def _library_name(self):
        libname = "jemalloc"
        if is_msvc(self):
            if self.options.shared:
                if self.settings.build_type == "Debug":
                    libname += "d"
            else:
                toolset = tools_legacy.msvs_toolset(self.settings)
                toolset_number = "".join(c for c in toolset if c in string.digits)
                libname += f"-vc{toolset_number}-{self._msvc_build_type}"
        else:
            if self.settings.os == "Windows":
                if not self.options.shared:
                    libname += "_s"
            else:
                if not self.options.shared and self.options.fPIC:
                    libname += "_pic"
        return libname

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if is_msvc(self):
            arch_subdir = {
                "x86_64": "x64",
                "x86": "x86",
            }[str(self.settings.arch)]
            copy(self, "*.lib",
                 src=os.path.join(self.source_folder, "msvc", arch_subdir, self._msvc_build_type),
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "*.dll",
                 src=os.path.join(self.source_folder, "msvc", arch_subdir, self._msvc_build_type),
                 dst=os.path.join(self.package_folder, "bin"))
            copy(self, "jemalloc.h",
                src=os.path.join(self.source_folder, "include", "jemalloc"),
                dst=os.path.join(self.package_folder, "include", "jemalloc"))
            shutil.copytree(
                os.path.join(self.source_folder, "include", "msvc_compat"),
                os.path.join(self.package_folder, "include", "msvc_compat"),
            )
        else:
            autotools = Autotools(self)
            autotools.configure()
            # Use install_lib_XXX and install_include to avoid mixing binaries and dll's
            autotools.make(target="install_lib_shared" if self.options.shared else "install_lib_static")
            autotools.make(target="install_include")
            if self.settings.os == "Windows" and self.settings.compiler == "gcc":
                rename(
                    self,
                    os.path.join(self.package_folder, "lib", "{}.lib".format(self._library_name)),
                    os.path.join(self.package_folder, "lib", "lib{}.a".format(self._library_name)),
                )
                if not self.options.shared:
                    os.unlink(os.path.join(self.package_folder, "lib", "jemalloc.lib"))

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "jemalloc")
        self.cpp_info.libs = [self._library_name]
        self.cpp_info.includedirs = [
            os.path.join(self.package_folder, "include"),
            os.path.join(self.package_folder, "include", "jemalloc"),
        ]
        if is_msvc(self):
            self.cpp_info.includedirs.append(os.path.join(self.package_folder, "include", "msvc_compat"))
        if not self.options.shared:
            self.cpp_info.defines = ["JEMALLOC_EXPORT="]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.extend(["dl", "pthread", "rt"])
