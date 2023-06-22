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
import os


required_conan_version = ">=1.45.0"


class OpenVDBConan(ConanFile):
    name = "openvdb"
    description = (
        "OpenVDB is an open source C++ library comprising a novel hierarchical data"
        "structure and a large suite of tools for the efficient storage and "
        "manipulation of sparse volumetric data discretized on three-dimensional grids."
    )
    license = "MPL-2.0"
    topics = ("voxel", "voxelizer", "volume-rendering", "fx")
    homepage = "https://github.com/AcademySoftwareFoundation/openvdb"
    url = "https://github.com/conan-io/conan-center-index"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_blosc": [True, False],
        "with_zlib": [True, False],
        "with_log4cplus": [True, False],
        "with_exr": [True, False],
        "simd": [None, "SSE42", "AVX"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_blosc": True,
        "with_zlib": True,
        "with_log4cplus": False,
        "with_exr": False,
        "simd": None,
    }

    @property
    def _compilers_min_version(self):
        return {
            "msvc": "191",
            "Visual Studio": "15",  # Should we check toolset?
            "gcc": "6.3.1",
            "clang": "3.8",
            "apple-clang": "3.8",
            "intel": "17",
        }

    def export_sources(self):
        copy(self, "CMakeLists.txt")
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("boost/1.79.0")
        self.requires("onetbb/2020.3")
        self.requires("openexr/2.5.7")  # required for IlmBase::Half
        if self.options.with_zlib:
            self.requires("zlib/1.2.12")
        if self.options.with_exr:
            # Not necessary now. Required for IlmBase::IlmImf
            self.requires("openexr/2.5.7")
        if self.options.with_blosc:
            self.requires("c-blosc/1.21.1")
        if self.options.with_log4cplus:
            self.requires("log4cplus/2.0.7")

    def _check_compilier_version(self):
        compiler = str(self.settings.compiler)
        version = Version(self.settings.compiler.version)
        minimum_version = self._compilers_min_version.get(compiler, False)
        if minimum_version and version < minimum_version:
            raise ConanInvalidConfiguration(
                f"{self.name} requires a {compiler} version greater than {minimum_version}"
            )

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 14)
        if self.settings.arch not in ("x86", "x86_64"):
            if self.options.simd:
                raise ConanInvalidConfiguration("Only intel architectures support SSE4 or AVX.")
        self._check_compilier_version()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _patch_sources(self):
        apply_conandata_patches(self)
        # Remove FindXXX files from OpenVDB. Let Conan do the job
        rm(self, "Find*", os.path.join(self.source_folder, "cmake"), recursive=True)
        with open("FindBlosc.cmake", "w") as f:
            f.write(
                """find_package(c-blosc)
if(c-blosc_FOUND)
    add_library(blosc INTERFACE)
    target_link_libraries(blosc INTERFACE c-blosc::c-blosc)
    add_library(Blosc::blosc ALIAS blosc)
endif()
"""
            )
        with open("FindIlmBase.cmake", "w") as f:
            f.write(
                """find_package(OpenEXR)
if(OpenEXR_FOUND)
  add_library(Half INTERFACE)
  add_library(IlmThread INTERFACE)
  add_library(Iex INTERFACE)
  add_library(Imath INTERFACE)
  add_library(IlmImf INTERFACE)
  target_link_libraries(Half INTERFACE OpenEXR::OpenEXR)
  target_link_libraries(IlmThread INTERFACE OpenEXR::OpenEXR)
  target_link_libraries(Iex INTERFACE OpenEXR::OpenEXR)
  target_link_libraries(Imath INTERFACE OpenEXR::OpenEXR)
  target_link_libraries(IlmImf INTERFACE OpenEXR::OpenEXR)
  add_library(IlmBase::Half ALIAS Half)
  add_library(IlmBase::IlmThread ALIAS IlmThread)
  add_library(IlmBase::Iex ALIAS Iex)
  add_library(IlmBase::Imath ALIAS Imath)
  add_library(OpenEXR::IlmImf ALIAS IlmImf)
 endif()
 """
            )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def generate(self):
        tc = CMakeToolchain(self)
        # exposed options
        tc.variables["USE_BLOSC"] = self.options.with_blosc
        tc.variables["USE_ZLIB"] = self.options.with_zlib
        tc.variables["USE_LOG4CPLUS"] = self.options.with_log4cplus
        tc.variables["USE_EXR"] = self.options.with_exr
        tc.variables["OPENVDB_SIMD"] = self.options.simd

        tc.variables["OPENVDB_CORE_SHARED"] = self.options.shared
        tc.variables["OPENVDB_CORE_STATIC"] = not self.options.shared

        # All available options but not exposed yet. Set to default values
        tc.variables["OPENVDB_BUILD_CORE"] = True
        tc.variables["OPENVDB_BUILD_BINARIES"] = False
        tc.variables["OPENVDB_BUILD_PYTHON_MODULE"] = False
        tc.variables["OPENVDB_BUILD_UNITTESTS"] = False
        tc.variables["OPENVDB_BUILD_DOCS"] = False
        tc.variables["OPENVDB_BUILD_HOUDINI_PLUGIN"] = False
        tc.variables["OPENVDB_BUILD_HOUDINI_ABITESTS"] = False

        tc.variables["OPENVDB_BUILD_AX"] = False
        tc.variables["OPENVDB_BUILD_AX_BINARIES"] = False
        tc.variables["OPENVDB_BUILD_AX_UNITTESTS"] = False

        tc.variables["OPENVDB_BUILD_MAYA_PLUGIN"] = False
        tc.variables["OPENVDB_ENABLE_RPATH"] = False
        tc.variables["OPENVDB_CXX_STRICT"] = False
        tc.variables["USE_HOUDINI"] = False
        tc.variables["USE_MAYA"] = False
        tc.variables["USE_STATIC_DEPENDENCIES"] = False
        tc.variables["USE_PKGCONFIG"] = False
        tc.variables["OPENVDB_INSTALL_CMAKE_MODULES"] = False

        tc.variables["Boost_USE_STATIC_LIBS"] = not self.options["boost"].shared
        tc.variables["OPENEXR_USE_STATIC_LIBS"] = not self.options["openexr"].shared

        tc.variables["OPENVDB_DISABLE_BOOST_IMPLICIT_LINKING"] = True

        tc.generate()

    def package(self):
        copy(self, "LICENSE", dst="licenses", src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "OpenVDB")
        self.cpp_info.set_property("cmake_target_name", "OpenVDB::openvdb")

        # TODO: back to global scope in conan v2 once cmake_find_package_* generators removed
        lib_prefix = "lib" if is_msvc(self) and not self.options.shared else ""
        self.cpp_info.components["openvdb-core"].libs = [lib_prefix + "openvdb"]

        lib_define = "OPENVDB_DLL" if self.options.shared else "OPENVDB_STATICLIB"
        self.cpp_info.components["openvdb-core"].defines.append(lib_define)

        if self.settings.os == "Windows":
            self.cpp_info.components["openvdb-core"].defines.append("_WIN32")
            self.cpp_info.components["openvdb-core"].defines.append("NOMINMAX")

        if not self.options["openexr"].shared:
            self.cpp_info.components["openvdb-core"].defines.append("OPENVDB_OPENEXR_STATICLIB")
        if self.options.with_exr:
            self.cpp_info.components["openvdb-core"].defines.append("OPENVDB_TOOLS_RAYTRACER_USE_EXR")
        if self.options.with_log4cplus:
            self.cpp_info.components["openvdb-core"].defines.append("OPENVDB_USE_LOG4CPLUS")

        self.cpp_info.components["openvdb-core"].requires = [
            "boost::iostreams",
            "boost::system",
            "onetbb::onetbb",
            "openexr::openexr",  # should be "openexr::Half",
        ]
        if self.settings.os == "Windows":
            self.cpp_info.components["openvdb-core"].requires.append("boost::disable_autolinking")

        if self.options.with_zlib:
            self.cpp_info.components["openvdb-core"].requires.append("zlib::zlib")
        if self.options.with_blosc:
            self.cpp_info.components["openvdb-core"].requires.append("c-blosc::c-blosc")
        if self.options.with_log4cplus:
            self.cpp_info.components["openvdb-core"].requires.append("log4cplus::log4cplus")

        if self.settings.os in ("Linux", "FreeBSD"):
            self.cpp_info.components["openvdb-core"].system_libs = ["pthread"]

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.names["cmake_find_package"] = "OpenVDB"
        self.cpp_info.names["cmake_find_package_multi"] = "OpenVDB"
        self.cpp_info.components["openvdb-core"].names["cmake_find_package"] = "openvdb"
        self.cpp_info.components["openvdb-core"].names["cmake_find_package_multi"] = "openvdb"
        self.cpp_info.components["openvdb-core"].set_property("cmake_target_name", "OpenVDB::openvdb")
