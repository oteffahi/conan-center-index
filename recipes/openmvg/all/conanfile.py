from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd, valid_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rename, rm, rmdir
from conan.tools.microsoft import is_msvc
from conan.tools.scm import Version
import glob
import os

required_conan_version = ">=1.53.0"


class Openmvgconan(ConanFile):
    name = "openmvg"
    description = (
        "OpenMVG provides an end-to-end 3D reconstruction from images framework "
        "compounded of libraries, binaries, and pipelines."
    )
    license = "MPL-2.0"
    topics = (
        "computer-vision",
        "geometry",
        "structure-from-motion",
        "sfm",
        "multi-view-geometry",
        "photogrammetry",
        "3d-reconstruction",
    )
    homepage = "https://github.com/openMVG/openMVG"
    url = "https://github.com/conan-io/conan-center-index"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_openmp": [True, False],
        "with_avx": [False, "avx", "avx2"],
        "programs": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_openmp": False,
        "with_avx": False,
        "programs": True,
    }

    short_paths = True

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.arch not in ["x86", "x86_64"]:
            del self.options.with_avx

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cereal/1.3.2", transitive_headers=True)
        self.requires("ceres-solver/2.1.0")
        self.requires("coin-clp/1.17.7")
        self.requires("coin-lemon/1.3.1")
        self.requires("coin-osi/0.108.7")
        self.requires("coin-utils/2.11.6")
        self.requires("eigen/3.4.0", transitive_headers=True)
        self.requires("flann/1.9.2", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg/9e")
        self.requires("libpng/1.6.39")
        self.requires("libtiff/4.5.0")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "11")

        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) < "7":
            raise ConanInvalidConfiguration(
                f"{self.ref} can' be built by gcc < 7 due to usage of some ceres-solver templated code "
                "which hits a bug in gcc < 7: https://gcc.gnu.org/bugzilla/show_bug.cgi?id=56480"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OpenMVG_BUILD_SHARED"] = self.options.shared
        tc.variables["OpenMVG_BUILD_TESTS"] = False
        tc.variables["OpenMVG_BUILD_DOC"] = False
        tc.variables["OpenMVG_BUILD_EXAMPLES"] = False
        tc.variables["OpenMVG_BUILD_OPENGL_EXAMPLES"] = False
        tc.variables["OpenMVG_BUILD_SOFTWARES"] = self.options.programs
        tc.variables["OpenMVG_BUILD_GUI_SOFTWARES"] = False
        tc.variables["OpenMVG_BUILD_COVERAGE"] = False
        tc.variables["OpenMVG_USE_OPENMP"] = self.options.with_openmp
        tc.variables["OpenMVG_USE_OPENCV"] = False
        tc.variables["OpenMVG_USE_OCVSIFT"] = False
        # OpenMVG expects these CMake variables to be set automatically by a custom OptimizeForArchitecture macro
        # but this macro is fragile and broken in case of cross-build. Moreover it may lead to non-portable binaries.
        # Therefore macro is disabled through patch and we allow users to decide whether they want specific avx
        # optimization.
        tc.variables["USE_SSE2"] = self.settings.arch in ["x86", "x86_64"]
        tc.variables["USE_AVX"] = self.options.get_safe("with_avx") in ["avx", "avx2"]
        tc.variables["USE_AVX2"] = self.options.get_safe("with_avx") == "avx2"
        # Even though openmvg requires C++11, recent versions of cereal require C++14
        # and targets generated by CMakeDeps don't propagate compile features (yet?)
        # see https://github.com/conan-io/conan/issues/10281
        if Version(self.dependencies["ceres-solver"].ref.version) >= "2.0.0" and not valid_min_cppstd(
            self, "14"
        ):
            tc.variables["CMAKE_CXX_STANDARD"] = "14"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure(build_script_folder=os.path.join(self.source_folder, "src"))
        cmake.build()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.cmake", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share", "openMVG", "cmake"))
        rename(
            self, src=os.path.join(self.package_folder, "share"), dst=os.path.join(self.package_folder, "res")
        )
        for dll_file in glob.glob(os.path.join(self.package_folder, "lib", "*.dll")):
            rename(
                self, src=dll_file, dst=os.path.join(self.package_folder, "bin", os.path.basename(dll_file))
            )

    @property
    def _openmvg_components(self):
        return {
            "openmvg_camera": {"target": "openMVG_camera", "requires": ["openmvg_numeric", "cereal::cereal"]},
            "openmvg_exif": {
                "target": "openMVG_exif",
                "libs": ["openMVG_exif"],
                "requires": ["openmvg_easyexif"],
            },
            "openmvg_features": {
                "target": "openMVG_features",
                "libs": ["openMVG_features"],
                "requires": ["openmvg_fast", "openmvg_stlplus", "eigen::eigen", "cereal::cereal"],
            },
            "openmvg_geodesy": {"target": "openMVG_geodesy", "requires": ["openmvg_numeric"]},
            "openmvg_geometry": {
                "target": "openMVG_geometry",
                "libs": ["openMVG_geometry"],
                "requires": ["openmvg_numeric", "openmvg_linearprogramming", "cereal::cereal"],
            },
            "openmvg_graph": {"target": "openMVG_graph", "requires": ["coin-lemon::coin-lemon"]},
            "openmvg_image": {
                "target": "openMVG_image",
                "libs": ["openMVG_image"],
                "requires": ["openmvg_numeric", "libjpeg::libjpeg", "libpng::libpng", "libtiff::libtiff"],
            },
            "openmvg_linearprogramming": {
                "target": "openMVG_linearProgramming",
                "libs": ["openMVG_linearProgramming"],
                "requires": [
                    "openmvg_numeric",
                    "coin-clp::coin-clp",
                    "coin-osi::coin-osi",
                    "coin-utils::coin-utils",
                ],
            },
            "openmvg_linftycomputervision": {
                "target": "openMVG_lInftyComputerVision",
                "libs": ["openMVG_lInftyComputerVision"],
                "requires": ["openmvg_linearprogramming", "openmvg_multiview"],
            },
            "openmvg_matching": {
                "target": "openMVG_matching",
                "libs": ["openMVG_matching"],
                "requires": ["openmvg_features", "openmvg_stlplus", "cereal::cereal", "flann::flann"],
                "system_libs": [(self.settings.os in ["Linux", "FreeBSD"], ["pthread"])],
            },
            "openmvg_kvld": {
                "target": "openMVG_kvld",
                "libs": ["openMVG_kvld"],
                "requires": ["openmvg_features", "openmvg_image"],
            },
            "openmvg_matching_image_collection": {
                "target": "openMVG_matching_image_collection",
                "libs": ["openMVG_matching_image_collection"],
                "requires": ["openmvg_matching", "openmvg_multiview"],
            },
            "openmvg_multiview": {
                "target": "openMVG_multiview",
                "libs": ["openMVG_multiview"],
                "requires": ["openmvg_numeric", "openmvg_graph", "ceres-solver::ceres-solver"],
            },
            "openmvg_numeric": {
                "target": "openMVG_numeric",
                "libs": ["openMVG_numeric"],
                "requires": ["eigen::eigen"],
                "defines": [(is_msvc(self), ["_USE_MATH_DEFINES"])],
            },
            "openmvg_robust_estimation": {
                "target": "openMVG_robust_estimation",
                "libs": ["openMVG_robust_estimation"],
                "requires": ["openmvg_numeric"],
            },
            "openmvg_sfm": {
                "target": "openMVG_sfm",
                "libs": ["openMVG_sfm"],
                "requires": [
                    "openmvg_geometry",
                    "openmvg_features",
                    "openmvg_graph",
                    "openmvg_matching",
                    "openmvg_multiview",
                    "openmvg_image",
                    "openmvg_linftycomputervision",
                    "openmvg_system",
                    "openmvg_stlplus",
                    "cereal::cereal",
                    "ceres-solver::ceres-solver",
                ],
            },
            "openmvg_system": {
                "target": "openMVG_system",
                "libs": ["openMVG_system"],
                "requires": ["openmvg_numeric"],
            },
            # vendored libs
            "openmvg_easyexif": {"target": "openMVG_easyexif", "libs": ["openMVG_easyexif"]},
            "openmvg_fast": {"target": "openMVG_fast", "libs": ["openMVG_fast"]},
            "openmvg_stlplus": {"target": "openMVG_stlplus", "libs": ["openMVG_stlplus"]},
            "openmvg_vlsift": {"target": "vlsift", "libs": ["vlsift"]},
        }

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenMVG")

        for component, values in self._openmvg_components.items():
            target = values["target"]
            libs = values.get("libs", [])
            defines = []
            for _condition, _defines in values.get("defines", []):
                if _condition:
                    defines.extend(_defines)
            system_libs = []
            for _condition, _system_libs in values.get("system_libs", []):
                if _condition:
                    system_libs.extend(_system_libs)

            self.cpp_info.components[component].set_property("cmake_target_name", f"OpenMVG::{target}")
            if libs:
                self.cpp_info.components[component].libs = libs
            self.cpp_info.components[component].defines = defines
            self.cpp_info.components[component].requires = values.get("requires", [])
            self.cpp_info.components[component].system_libs = system_libs
            self.cpp_info.components[component].resdirs = ["res"]

            # TODO: to remove in conan v2
            self.cpp_info.components[component].names["cmake_find_package"] = target
            self.cpp_info.components[component].names["cmake_find_package_multi"] = target

        # TODO: to remove in conan v2
        self.cpp_info.names["cmake_find_package"] = "OpenMVG"
        self.cpp_info.names["cmake_find_package_multi"] = "OpenMVG"
        if self.options.programs:
            self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
