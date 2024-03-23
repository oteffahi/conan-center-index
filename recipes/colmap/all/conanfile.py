import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import collect_libs, copy, get, rm, rmdir

required_conan_version = ">=1.53.0"


class ColmapConan(ConanFile):
    name = "colmap"
    description = (
        "COLMAP is a general-purpose Structure-from-Motion (SfM) and Multi-View Stereo (MVS) pipeline with a graphical and command-line interface."
        " It offers a wide range of features for reconstruction of ordered and unordered image collections."
    )
    license = "BSD-3-Clause"
    homepage = "https://colmap.github.io/"
    url = "https://github.com/conan-io/conan-center-index"
    topics = ""

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "enable_cuda": [True, False],
        "enable_openmp": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "enable_cuda": False,
        "enable_openmp": False,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def export_sources(self):
        pass

    def requirements(self):
        self.requires("boost/1.84.0", force=True)
        self.requires("ceres-solver/2.2.0")
        self.requires("cgal/5.6.1")
        self.requires("eigen/3.4.0")
        self.requires("flann/1.9.2")
        self.requires("freeimage/3.18.0")
        self.requires("gflags/2.2.2")
        self.requires("glew/2.2.0")
        self.requires("glog/0.7.0")
        # self.requires("qt/6.6.2")
        self.requires("sqlite3/3.45.2")

        self.requires("libpng/[>=1.6 <2]", override=True)
        self.requires("xz_utils/5.6.1", override=True)

    def validate(self):
        pass

    def build_requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["TESTS_ENABLED"] = False
        tc.variables["CUDA_ENABLED"] = self.options.enable_cuda
        tc.variables["OPENMP_ENABLED"] = self.options.enable_openmp
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        pass

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "COPYING.txt", self.source_folder, os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        rm(self, "*.bat", self.package_folder)
        rmdir(self, os.path.join(self.package_folder, "include", "colmap", "exe"))
        rmdir(self, os.path.join(self.package_folder, "include", "colmap", "tools"))
        rmdir(self, os.path.join(self.package_folder, "include", "colmap", "ui", "media"))
        rmdir(self, os.path.join(self.package_folder, "include", "colmap", "ui", "shaders"))

    def package_info(self):
        self.cpp_info.libs = collect_libs(self)
