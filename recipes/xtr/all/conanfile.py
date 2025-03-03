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
import os

required_conan_version = ">=1.53.0"


class XtrConan(ConanFile):
    name = "xtr"
    description = "C++ Logging Library for Low-latency or Real-time Environments"
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/choll/xtr"
    topics = ("logging", "logger")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_exceptions": [True, False],
        "enable_lto": [True, False],
        "enable_io_uring": ["auto", True, False],
        "enable_io_uring_sqpoll": [True, False],
        "sink_capacity_kb": "ANY",
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_exceptions": True,
        "enable_lto": False,
        "enable_io_uring": "auto",
        "enable_io_uring_sqpoll": False,
        "sink_capacity_kb": None,
    }

    def config_options(self):
        if Version(self.version) < "1.0.1":
            self.options.rm_safe("sink_capacity_kb")
        if Version(self.version) < "2.0.0":
            self.options.rm_safe("enable_io_uring")
            self.options.rm_safe("enable_io_uring_sqpoll")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        self.requires("fmt/10.1.1")
        # Require liburing on any Linux system as a run-time check will be
        # done to detect if the host kernel supports io_uring.
        if (
            Version(self.version) >= "2.0.0"
            and self.settings.os in ["Linux", "FreeBSD"]
            and self.options.get_safe("enable_io_uring")
        ):
            self.requires("liburing/2.2")

    def validate(self):
        if self.settings.os not in ("FreeBSD", "Linux"):
            raise ConanInvalidConfiguration(f"Unsupported os={self.settings.os}")
        if self.settings.compiler not in ("gcc", "clang"):
            raise ConanInvalidConfiguration(f"Unsupported compiler={self.settings.compiler}")
        if self.settings.arch not in ("x86_64",):
            raise ConanInvalidConfiguration(f"Unsupported arch={self.settings.arch}")
        if (
            Version(self.version) < "2.0.0"
            and self.settings.compiler == "clang"
            and self.settings.compiler.libcxx == "libc++"
        ):
            raise ConanInvalidConfiguration(f"Use at least version 2.0.0 for libc++ compatibility")
        if self.options.get_safe("enable_io_uring_sqpoll") and not self.options.get_safe("enable_io_uring"):
            raise ConanInvalidConfiguration(f"io_uring must be enabled if io_uring_sqpoll is enabled")
        if (
            self.options.get_safe("sink_capacity_kb")
            and not str(self.options.get_safe("sink_capacity_kb")).isdigit()
        ):
            raise ConanInvalidConfiguration(f"The option 'sink_capacity_kb' must be an integer")

        minimal_cpp_standard = 20
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, minimal_cpp_standard)

        minimum_version = {"gcc": 10, "clang": 12}
        compiler = str(self.settings.compiler)
        version = Version(self.settings.compiler.version)

        if version < minimum_version[compiler]:
            raise ConanInvalidConfiguration(
                f"{self.name} requires {self.settings.compiler} version {minimum_version[compiler]} or later"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # TODO: fill in generate()
        pass

    def _get_defines(self):
        defines = []
        enable_io_uring = self.options.get_safe("enable_io_uring")
        if enable_io_uring in (True, False):
            defines += ["XTR_USE_IO_URING={}".format(int(bool(enable_io_uring)))]
        if self.options.get_safe("enable_io_uring_sqpoll"):
            defines += ["XTR_IO_URING_POLL=1"]
        capacity = self.options.get_safe("sink_capacity_kb")
        if capacity:
            defines += ["XTR_SINK_CAPACITY={}".format(int(capacity) * 1024)]
        return defines

    def build(self):
        # FIXME: should be done in validate (but version is not yet available there)
        if Version(self.dependencies["fmt"].ref.version) < 6:
            raise ConanInvalidConfiguration("The version of fmt must >= 6.0.0")
        if Version(self.dependencies["fmt"].ref.version) == "8.0.0" and self.settings.compiler == "clang":
            raise ConanInvalidConfiguration(
                "fmt/8.0.0 is known to not work with clang (https://github.com/fmtlib/fmt/issues/2377)"
            )

        autotools = AutoToolsBuildEnvironment(self)
        env_build_vars = autotools.vars
        # Conan uses LIBS, presumably following autotools conventions, while
        # the XTR makefile follows GNU make conventions and uses LDLIBS
        env_build_vars["LDLIBS"] = env_build_vars["LIBS"]
        # fPIC and Release/Debug/RelWithDebInfo etc are set via CXXFLAGS,
        # CPPFLAGS etc.
        env_build_vars["EXCEPTIONS"] = str(int(bool(self.options.enable_exceptions)))
        env_build_vars["LTO"] = str(int(bool(self.options.enable_lto)))
        env_build_vars["CXXFLAGS"] += "".join([" -D{}".format(d) for d in self._get_defines()])
        autotools.make(vars=env_build_vars)
        autotools.make(vars=env_build_vars, target="xtrctl")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*.hpp",
             src=os.path.join(self.source.folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*/libxtr.a",
             src=os.path.join(self.source.folder, "build"),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*/xtrctl",
             src=os.path.join(self.source.folder, "build"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

        rmdir(self, os.path.join(self.package_folder, "man"))

    def package_info(self):
        self.cpp_info.libs = ["xtr"]
        self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.defines = self._get_defines()
        bin_path = os.path.join(self.package_folder, "bin")
        self.output.info(f"Appending PATH environment variable: {bin_path}")
        self.env_info.PATH.append(bin_path)
