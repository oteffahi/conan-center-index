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
import functools
from itertools import product
import os

required_conan_version = ">=1.33.0"


class OpenFstConan(ConanFile):
    name = "openfst"
    description = "A library for constructing, combining, optimizing and searching weighted finite-state-transducers (FSTs)."
    topics = ("asr", "fst", "wfst", "openfst")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://www.openfst.org/twiki/bin/view/FST/WebHome"
    license = "Apache-2.0"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_bin": [True, False],
        "enable_compact_fsts": [True, False],
        "enable_compress": [True, False],
        "enable_const_fsts": [True, False],
        "enable_far": [True, False],
        "enable_grm": [True, False],
        "enable_linear_fsts": [True, False],
        "enable_lookahead_fsts": [True, False],
        "enable_mpdt": [True, False],
        "enable_ngram_fsts": [True, False],
        "enable_pdt": [True, False],
        "enable_special": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_bin": True,
        "enable_compact_fsts": False,
        "enable_compress": False,
        "enable_const_fsts": False,
        "enable_far": False,
        "enable_grm": True,
        "enable_linear_fsts": False,
        "enable_lookahead_fsts": False,
        "enable_mpdt": False,
        "enable_ngram_fsts": False,
        "enable_pdt": False,
        "enable_special": False,
    }

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os != "Linux":
            raise ConanInvalidConfiguration("OpenFst is only supported on linux")

        compilers = {
            "gcc": "8",
            "clang": "7",
        }

        if self.settings.compiler.cppstd:
            check_min_cppstd(self, 17)
        minimum_compiler = compilers.get(str(self.settings.compiler))
        if minimum_compiler:
            if Version(self.settings.compiler.version) < minimum_compiler:
                raise ConanInvalidConfiguration(
                    f"{self.name} requires c++17, which your compiler does not support."
                )
        else:
            self.output.warn(
                f"{self.name} requires c++17, but this compiler is unknown to this recipe. Assuming your compiler supports c++17."
            )

        # Check stdlib ABI compatibility
        if self.settings.compiler == "gcc" and self.settings.compiler.libcxx != "libstdc++11":
            raise ConanInvalidConfiguration(
                'Using %s with GCC requires "compiler.libcxx=libstdc++11"' % self.name
            )
        elif self.settings.compiler == "clang" and self.settings.compiler.libcxx not in [
            "libstdc++11",
            "libc++",
        ]:
            raise ConanInvalidConfiguration(
                'Using %s with Clang requires either "compiler.libcxx=libstdc++11"'
                ' or "compiler.libcxx=libc++"' % self.name
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    @functools.lru_cache(1)
    def _configure_autotools(self):
        autotools = AutoToolsBuildEnvironment(self)
        yes_no = lambda v: "yes" if v else "no"
        args = [
            "--with-pic={}".format(yes_no(self.options.get_safe("fPIC", True))),
            "--enable-shared={}".format(yes_no(self.options.shared)),
            "--enable-static={}".format(yes_no(not self.options.shared)),
            "--enable-bin={}".format(yes_no(self.options.enable_bin)),
            "--enable-compact-fsts={}".format(yes_no(self.options.enable_compact_fsts)),
            "--enable-compress={}".format(yes_no(self.options.enable_compress)),
            "--enable-const-fsts={}".format(yes_no(self.options.enable_const_fsts)),
            "--enable-far={}".format(yes_no(self.options.enable_far)),
            "--enable-grm={}".format(yes_no(self.options.enable_grm)),
            "--enable-linear-fsts={}".format(yes_no(self.options.enable_linear_fsts)),
            "--enable-lookahead-fsts={}".format(yes_no(self.options.enable_lookahead_fsts)),
            "--enable-mpdt={}".format(yes_no(self.options.enable_mpdt)),
            "--enable-ngram-fsts={}".format(yes_no(self.options.enable_ngram_fsts)),
            "--enable-pdt={}".format(yes_no(self.options.enable_pdt)),
            "--enable-special={}".format(yes_no(self.options.enable_special)),
            "LIBS=-lpthread",
        ]
        autotools.configure(args=args, configure_dir=self.source_folder)
        return autotools

    def export_sources(self):
        export_conandata_patches(self)

    def _patch_sources(self):
        apply_conandata_patches(self)

    def build(self):
        self._patch_sources()
        autotools = self._configure_autotools()
        autotools.make()

    def package(self):
        copy(self, pattern="COPYING", dst="licenses", src=self.source_folder)
        autotools = self._configure_autotools()
        autotools.install()

        lib_dir = os.path.join(self.package_folder, "lib")
        lib_subdir = os.path.join(self.package_folder, "lib", "fst")
        if os.path.exists(lib_subdir):
            for fn in os.listdir(lib_subdir):
                rename(self, os.path.join(lib_subdir, fn), os.path.join(lib_dir, "lib{}".format(fn)))
            rmdir(self, lib_subdir)

        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.la", lib_dir, recursive=True)

    @property
    def _get_const_fsts_libs(self):
        return ["const{}-fst".format(n) for n in [8, 16, 64]]

    @property
    def _get_compact_fsts_libs(self):
        return [
            "compact{}_{}-fst".format(n, fst)
            for n, fst in product(
                [8, 16, 64], ["acceptor", "string", "unweighted_acceptor", "unweighted", "weighted_string"]
            )
        ]

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenFst")
        self.cpp_info.set_property("cmake_target_name", "OpenFst::OpenFst")
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.names["cmake_find_package"] = "OpenFst"
        self.cpp_info.names["cmake_find_package_multi"] = "OpenFst"

        self.cpp_info.libs = ["fst"]

        if self.options.enable_compact_fsts:
            self.cpp_info.libs.append("fstcompact")
        if self.options.enable_const_fsts:
            self.cpp_info.libs.append("fstconst")
        if self.options.enable_far or self.options.enable_grm:
            self.cpp_info.libs.append("fstfar")
        if self.options.enable_lookahead_fsts:
            self.cpp_info.libs.append("fstlookahead")
        if self.options.enable_ngram_fsts:
            self.cpp_info.libs.append("fstngram")
        if self.options.enable_special:
            self.cpp_info.libs.append("fstspecial")

        if self.options.enable_bin:
            self.cpp_info.libs.append("fstscript")
            if self.options.enable_compress:
                self.cpp_info.libs.append("fstcompressscript")
            if self.options.enable_compact_fsts:
                self.cpp_info.libs.extend(self._get_compact_fsts_libs)
            if self.options.enable_const_fsts:
                self.cpp_info.libs.extend(self._get_const_fsts_libs)
            if self.options.enable_far or self.options.enable_grm:
                self.cpp_info.libs.append("fstfarscript")
            if self.options.enable_linear_fsts:
                self.cpp_info.libs.append("fstlinearscript")
            if self.options.enable_mpdt or self.options.enable_grm:
                self.cpp_info.libs.append("fstmpdtscript")
            if self.options.enable_pdt or self.options.enable_grm:
                self.cpp_info.libs.append("fstpdtscript")

            bindir = os.path.join(self.package_folder, "bin")
            self.output.info("Appending PATH environment var: {}".format(bindir))
            self.env_info.PATH.append(bindir)

        self.cpp_info.system_libs = ["pthread", "dl", "m"]
