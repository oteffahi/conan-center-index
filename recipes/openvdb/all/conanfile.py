import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, rm, replace_in_file, export_conandata_patches, apply_conandata_patches
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version

required_conan_version = ">=1.53.0"


class OpenVDBConan(ConanFile):
    name = "openvdb"
    description = (
        "OpenVDB is an open source C++ library comprising a novel hierarchical data"
        "structure and a large suite of tools for the efficient storage and "
        "manipulation of sparse volumetric data discretized on three-dimensional grids."
    )
    license = "MPL-2.0"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/AcademySoftwareFoundation/openvdb"
    topics = ("voxel", "voxelizer", "volume-rendering", "fx", "vdb")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "build_ax": [True, False],
        "simd": [None, "SSE42", "AVX"],
        "use_colored_output": [True, False],
        "use_delayed_loading": [True, False],
        "use_explicit_instantiation": [True, False],
        "use_imath_half": [True, False],
        "with_blosc": [True, False],
        # Deprecated because EXR is only used when building executables, which the recipe does not support
        "with_exr": ["deprecated", True, False],
        "with_log4cplus": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "build_ax": False,
        "simd": None,
        "use_colored_output": False,
        "use_delayed_loading": False,
        "use_explicit_instantiation": False,
        "use_imath_half": False,
        "with_blosc": True,
        "with_exr": "deprecated",
        "with_log4cplus": False,
        "with_zlib": True,
    }
    options_description = {
        "build_ax": "Build the OpenVDB AX library.",
        "simd": (
            "Choose whether to enable SIMD compiler flags or not. "
            "Although not required, it is strongly recommended to enable SIMD. AVX implies SSE42."
        ),
        "use_colored_output": "Always produce ANSI-colored output (GNU/Clang only).",
        "use_delayed_loading": "Build the core OpenVDB library with delayed-loading.",
        "use_explicit_instantiation": (
            "Use explicit instantiation for all supported classes and methods against a pre-defined "
            "list of OpenVDB trees. This makes the core library larger and slower to compile, but speeds up "
            "the compilation of all dependent code by bypassing the expensive template instantiation. "
            "Disabled by default in ConanCenter to avoid excessive memory usage during compilation."
        ),
        "use_imath_half": (
            "Use the definition of half-precision floating point types from the Imath library. "
            "If False, the embedded definition provided by OpenVDB is used. "
            "You may set this to on to force Imath half to be used if you know it to be required."
        ),
        "with_blosc": "Use Blosc for improved disk compression. Recommended.",
        "with_log4cplus": "Use log4cplus for improved OpenVDB Logging.",
        "with_zlib": "Use ZLib for disk serialization compression. ZLib can only be disabled if Blosc is also disabled.",
    }

    @property
    def _min_cppstd(self):
        return 17 if Version(self.version) >= "10.0.0" else 14

    @property
    def _compilers_min_version(self):
        if Version(self.version) >= "10.0.0":
            # https://github.com/AcademySoftwareFoundation/openvdb/blob/v10.0.1/doc/dependencies.txt#L56-L84
            return {
                "msvc": "192.8",
                "Visual Studio": "16",
                "gcc": "9.3.1",
                "clang": "5.0",
                "apple-clang": "12.0",
                "intel-cc": "19",
            }
        if Version(self.version) >= "9.0.0":
            # https://github.com/AcademySoftwareFoundation/openvdb/blob/v9.1.0/doc/dependencies.txt#L56-L84
            return {
                "msvc": "191.0",
                "Visual Studio": "15",
                "gcc": "6.3.1",
                "clang": "3.8",
                "apple-clang": "10.0",
                "intel-cc": "17",
            }
        # https://github.com/AcademySoftwareFoundation/openvdb/blob/v8.2.0/doc/dependencies.txt#L55-L81
        return {
            "msvc": "191.0",
            "Visual Studio": "15",
            "gcc": "6.3.1",
            "clang": "3.8",
            "apple-clang": "10.0",
            "intel-cc": "17",
        }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if is_msvc(self):
            # Supported by GCC and Clang only
            del self.options.use_colored_output
        if Version(self.version) < "10.0.0":
            del self.options.use_explicit_instantiation
            del self.options.use_delayed_loading
        elif Version(self.version) < "8.1.0":
            del self.options.use_imath_half

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def package_id(self):
        # with_exr is deprecated and has no effect
        del self.info.options.with_exr

    def requirements(self):
        # https://github.com/AcademySoftwareFoundation/openvdb/blob/v10.0.1/doc/dependencies.txt#L36-L84
        self.requires("boost/1.83.0", transitive_headers=True)
        # Shared builds fail when the transitive_libs=True params below are not explicitly set for some reason
        if Version(self.version) >= "9.0.0":
            self.requires("onetbb/2021.10.0", transitive_headers=True, transitive_libs=True)
        else:
            self.requires("onetbb/2020.3.3", transitive_headers=True, transitive_libs=True)
        if Version(self.version) < "8.1.0" or self.options.use_imath_half:
            if Version(self.version) >= "9.0.0":
                self.requires("imath/3.1.9", transitive_headers=True, transitive_libs=True)
            else:
                self.requires("openexr/2.5.7", transitive_headers=True, transitive_libs=True)
        if self.options.with_zlib:
            self.requires("zlib/1.2.13")
        if self.options.with_blosc:
            self.requires("c-blosc/1.21.5")
        if self.options.with_log4cplus:
            # TODO: OpenVDB requires log4cplus v1.*, which is not available in CCI
            self.requires("log4cplus/1.2.2", transitive_headers=True)

    def _check_compiler_version(self):
        def lazy_lt_semver(v1, v2):
            # Needed to ignore any minor versions if not specified in settings.compiler.version
            return all(int(p1) < int(p2) for p1, p2 in zip(str(v1).split("."), str(v2).split(".")))

        compiler = str(self.settings.compiler)
        minimum_version = self._compilers_min_version.get(compiler, False)
        if minimum_version and lazy_lt_semver(self.settings.compiler.version, minimum_version):
            raise ConanInvalidConfiguration(
                f"{self.name} requires a {compiler} version greater than {minimum_version}"
            )

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        if self.settings.arch not in ("x86", "x86_64"):
            if self.options.simd:
                raise ConanInvalidConfiguration("Only intel architectures support SSE4 or AVX.")
        self._check_compiler_version()

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def build_requirements(self):
        if Version(self.version) >= "10.0.0":
            self.tool_requires("cmake/[>=3.18 <4]")
        if self.options.build_ax:
            if self._settings_build.os == "Windows":
                self.tool_requires("winflexbison/2.5.24")
            else:
                self.tool_requires("bison/3.8.2")
                self.tool_requires("flex/2.6.4")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["Boost_USE_STATIC_LIBS"] = not self.dependencies["boost"].options.shared
        tc.cache_variables["OPENVDB_BUILD_AX"] = self.options.build_ax
        tc.cache_variables["OPENVDB_BUILD_BINARIES"] = False
        tc.cache_variables["OPENVDB_BUILD_CORE"] = True
        tc.cache_variables["OPENVDB_BUILD_DOCS"] = False
        tc.cache_variables["OPENVDB_BUILD_HOUDINI_ABITESTS"] = False
        tc.cache_variables["OPENVDB_BUILD_HOUDINI_PLUGIN"] = False
        tc.cache_variables["OPENVDB_BUILD_MAYA_PLUGIN"] = False
        tc.cache_variables["OPENVDB_BUILD_NANOVDB"] = False # nanovdb should be packaged separately in CCI
        tc.cache_variables["OPENVDB_BUILD_PYTHON_MODULE"] = False
        tc.cache_variables["OPENVDB_CORE_SHARED"] = self.options.shared
        tc.cache_variables["OPENVDB_CORE_STATIC"] = not self.options.shared
        tc.cache_variables["OPENVDB_CXX_STRICT"] = False
        tc.cache_variables["OPENVDB_DISABLE_BOOST_IMPLICIT_LINKING"] = True
        tc.cache_variables["OPENVDB_ENABLE_RPATH"] = True
        tc.cache_variables["OPENVDB_ENABLE_UNINSTALL"] = False
        tc.cache_variables["OPENVDB_FUTURE_DEPRECATION"] = True
        tc.cache_variables["OPENVDB_INSTALL_CMAKE_MODULES"] = False
        tc.cache_variables["OPENVDB_SIMD"] = self.options.simd
        tc.cache_variables["OPENVDB_USE_DELAYED_LOADING"] = self.options.get_safe("use_delayed_loading", False)
        tc.cache_variables["USE_AX"] = False # used only by Python bindings and the Houdini plugin
        tc.cache_variables["USE_BLOSC"] = self.options.with_blosc
        tc.cache_variables["USE_COLORED_OUTPUT"] = self.options.get_safe("use_colored_output", False)
        tc.cache_variables["USE_EXPLICIT_INSTANTIATION"] = self.options.get_safe("use_explicit_instantiation", False)
        tc.cache_variables["USE_EXR"] = False
        tc.cache_variables["USE_HOUDINI"] = False
        tc.cache_variables["USE_IMATH_HALF"] = self.options.get_safe("use_imath_half", False)
        tc.cache_variables["USE_LOG4CPLUS"] = self.options.with_log4cplus
        tc.cache_variables["USE_MAYA"] = False
        tc.cache_variables["USE_NANOVDB"] = False
        tc.cache_variables["USE_PKGCONFIG"] = False
        tc.cache_variables["USE_PNG"] = False
        tc.cache_variables["USE_STATIC_DEPENDENCIES"] = False
        tc.cache_variables["USE_TBB"] = True # Only affects the nanovdb component
        tc.cache_variables["USE_ZLIB"] = self.options.with_zlib
        tc.generate()

        tc = CMakeDeps(self)
        tc.set_property("c-blosc", "cmake_file_name", "Blosc")
        tc.set_property("c-blosc", "cmake_target_name", "Blosc::blosc")
        tc.set_property("openexr", "cmake_file_name", "IlmBase")
        tc.set_property("openexr::ilmbase_half", "cmake_target_name", "IlmBase::Half")
        tc.set_property("log4cplus", "cmake_target_name", "Log4cplus::log4cplus")
        tc.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)
        # Remove FindXXX files from OpenVDB. Let Conan do the job
        rm(self, "Find*.cmake", os.path.join(self.source_folder, "cmake"), recursive=True)
        cmakelists = os.path.join(self.source_folder, "openvdb", "openvdb", "CMakeLists.txt")
        for dep in ["TBB", "BLOSC", "ZLIB", "LOG4CPLUS", "ILMBASE"]:
            # Relax version checks in find_package(),
            # since the config/module files produced by CMakeDeps do not support gt major version checks
            replace_in_file(self, cmakelists, f"${{MINIMUM_{dep}_VERSION}}", "")
        replace_in_file(self, os.path.join(self.source_folder, "openvdb", "openvdb", "CMakeLists.txt"),
                        "OPENVDB_FUTURE_DEPRECATION", "FALSE")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "LICENSE",
             dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)
        cmake = CMake(self)
        cmake.install()

    @property
    def _public_defines(self):
        defines = []
        if self.options.shared:
            defines.append("OPENVDB_DLL")
        else:
            defines.append("OPENVDB_STATICLIB")
        if self.settings.os == "Windows":
            defines.append("_WIN32")
            defines.append("NOMINMAX")
        if self.options.with_log4cplus:
            defines.append("OPENVDB_USE_LOG4CPLUS")
        # if self.options.with_exr:
        #     defines.append("OPENVDB_TOOLS_RAYTRACER_USE_EXR")
        #     if not self.dependencies["openexr"].options.shared:
        #         defines.append("OPENVDB_OPENEXR_STATICLIB")
        return defines

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "both")
        self.cpp_info.set_property("cmake_file_name", "OpenVDB")
        self.cpp_info.set_property("cmake_target_name", "OpenVDB::openvdb")

        # TODO: back to global scope in conan v2 once cmake_find_package_* generators removed
        main_component = self.cpp_info.components["openvdb-core"]
        lib_prefix = "lib" if is_msvc(self) and not self.options.shared else ""
        main_component.libs = [lib_prefix + "openvdb"]
        main_component.defines = self._public_defines
        if self.settings.os in ("Linux", "FreeBSD"):
            main_component.system_libs = ["pthread"]

        main_component.requires = [
            "boost::iostreams",
            "boost::system",
            "onetbb::onetbb",
        ]
        if self.settings.os == "Windows":
            main_component.requires.append("boost::disable_autolinking")
        if self.options.with_zlib:
            main_component.requires.append("zlib::zlib")
        if self.options.with_blosc:
            main_component.requires.append("c-blosc::c-blosc")
        if self.options.with_log4cplus:
            main_component.requires.append("log4cplus::log4cplus")
        if Version(self.version) < "8.1.0" or self.options.use_imath_half:
            if Version(self.version) >= "9.0.0":
                main_component.requires.append("imath::imath")
            else:
                main_component.requires.append("openexr::ilmbase_half")

        # TODO: to remove in conan v2 once cmake_find_package_* generators removed
        self.cpp_info.names["cmake_find_package"] = "OpenVDB"
        self.cpp_info.names["cmake_find_package_multi"] = "OpenVDB"
        main_component.names["cmake_find_package"] = "openvdb"
        main_component.names["cmake_find_package_multi"] = "openvdb"
        main_component.set_property("cmake_target_name", "OpenVDB::openvdb")
