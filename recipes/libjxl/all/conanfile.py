import os

from conan import ConanFile
from conan.tools.build import cross_building, stdcpp_library, check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import replace_in_file, copy, get, rmdir, save, rm

required_conan_version = ">=1.53.0"


class LibjxlConan(ConanFile):
    name = "libjxl"
    description = "JPEG XL image format reference implementation"
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/libjxl/libjxl"
    topics = ("image", "jpeg-xl", "jxl", "jpeg")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("brotli/1.1.0")
        self.requires("highway/1.0.7")
        self.requires("lcms/2.14")

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.cache_variables["BUILD_TESTING"] = False
        tc.cache_variables["JPEGXL_STATIC"] = not self.options.shared  # applies to tools only
        tc.cache_variables["JPEGXL_ENABLE_BENCHMARK"] = False
        tc.cache_variables["JPEGXL_ENABLE_EXAMPLES"] = False
        tc.cache_variables["JPEGXL_ENABLE_MANPAGES"] = False
        tc.cache_variables["JPEGXL_ENABLE_SJPEG"] = False
        tc.cache_variables["JPEGXL_ENABLE_OPENEXR"] = False
        tc.cache_variables["JPEGXL_ENABLE_SKCMS"] = False
        tc.cache_variables["JPEGXL_ENABLE_TCMALLOC"] = False
        tc.cache_variables["JPEGXL_FORCE_SYSTEM_BROTLI"] = True
        tc.cache_variables["JPEGXL_FORCE_SYSTEM_LCMS2"] = True
        tc.cache_variables["JPEGXL_FORCE_SYSTEM_HWY"] = True
        tc.cache_variables["JPEGXL_FORCE_SYSTEM_GTEST"] = True
        if cross_building(self):
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

        deps = CMakeDeps(self)
        deps.set_property("brotli", "cmake_file_name", "Brotli")
        deps.set_property("highway", "cmake_file_name", "HWY")
        deps.set_property("lcms", "cmake_file_name", "LCMS2")
        deps.generate()

    @property
    def _atomic_required(self):
        return self.settings.get_safe("compiler.libcxx") in ["libstdc++", "libstdc++11"]

    def _patch_sources(self):
        # Disable tools and extras
        save(self, os.path.join(self.source_folder, "tools", "CMakeLists.txt"), "")
        save(self, os.path.join(self.source_folder, "lib", "jxl_extras.cmake"), "")
        # Inject Conan dependencies
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "add_subdirectory(third_party)",
                        ("find_package(LCMS2 REQUIRED CONFIG)\n"
                         "find_package(Brotli REQUIRED CONFIG)\n"
                         "find_package(HWY REQUIRED CONFIG)\n"
                         "link_libraries(brotli::brotli highway::highway lcms::lcms)\n")
                        )
        # Do not link directly against libraries
        for cmake in [
            self.source_path.joinpath("lib", "jxl.cmake"),
            self.source_path.joinpath("lib", "jpegli.cmake"),
        ]:
            content = cmake.read_text(encoding="utf8")
            for lib, replacement in [
                ("hwy", "highway::highway"),
                ("brotlicommon-static", "brotli::brotli"),
                ("brotlienc-static", "brotli::brotli"),
                ("brotlidec-static", "brotli::brotli"),
                ("lcms2", "lcms::lcms"),
            ]:
                content = content.replace(lib, replacement)
            cmake.write_text(content, encoding="utf8")
        # Avoid "INTERFACE_LIBRARY targets may only have whitelisted properties" error with Conan v1
        jxl_cmake = os.path.join(self.source_folder, "lib", "jxl.cmake")
        replace_in_file(self, jxl_cmake, '"$<BUILD_INTERFACE:$<TARGET_PROPERTY', "# ", strict=False)
        replace_in_file(self, jxl_cmake, "$<TARGET_PROPERTY", "# ", strict=False)
        # Skip custom FindAtomic and force the use of atomic library directly for libstdc++
        atomic_lib = "atomic" if self._atomic_required else ""
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "find_package(Atomics REQUIRED)",
                        "set(ATOMICS_FOUND TRUE)\n"
                        f"set(ATOMICS_LIBRARIES {atomic_lib})")

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
            rm(self, "*-static.lib", os.path.join(self.package_folder, "lib"))

    def _lib_name(self, name):
        if not self.options.shared and self.settings.os == "Windows":
            return name + "-static"
        return name

    def package_info(self):
        # jxl
        self.cpp_info.components["jxl"].set_property("pkg_config_name", "libjxl")
        self.cpp_info.components["jxl"].libs = [self._lib_name("jxl")]
        self.cpp_info.components["jxl"].requires = ["brotli::brotli", "highway::highway", "lcms::lcms"]
        if stdcpp_library(self):
            self.cpp_info.components["jxl"].system_libs.append(stdcpp_library(self))
        if self._atomic_required:
            self.cpp_info.components["jxl"].system_libs.append("atomic")
        if not self.options.shared:
            self.cpp_info.components["jxl"].defines.append("JXL_STATIC_DEFINE")

        # jxl_dec
        if not self.options.shared:
            self.cpp_info.components["jxl_dec"].set_property("pkg_config_name", "libjxl_dec")
            self.cpp_info.components["jxl_dec"].libs = [self._lib_name("jxl_dec")]
            self.cpp_info.components["jxl_dec"].requires = ["brotli::brotli", "highway::highway", "lcms::lcms"]
            if stdcpp_library(self):
                self.cpp_info.components["jxl_dec"].system_libs.append(stdcpp_library(self))

        # jxl_threads
        self.cpp_info.components["jxl_threads"].set_property("pkg_config_name", "libjxl_threads")
        self.cpp_info.components["jxl_threads"].libs = [self._lib_name("jxl_threads")]
        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.components["jxl_threads"].system_libs = ["pthread"]
        if stdcpp_library(self):
            self.cpp_info.components["jxl_threads"].system_libs.append(stdcpp_library(self))
        if not self.options.shared:
            self.cpp_info.components["jxl_threads"].defines.append("JXL_THREADS_STATIC_DEFINE")
