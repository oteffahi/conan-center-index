from conan import ConanFile
from conan.tools.microsoft import is_msvc
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy, rm, rmdir, load, save
from conan.tools.scm import Version
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
import os
import re

required_conan_version = ">=1.53.0"


class LibharuConan(ConanFile):
    name = "libharu"
    description = "Haru is a free, cross platform, open-sourced software library for generating PDF."
    license = "Zlib"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "http://libharu.org/"
    topics = ("pdf", "generate", "generator")

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

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        # src_folder must use the same source folder name the project
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("zlib/[>=1.2.11 <2]")
        self.requires("libpng/1.6.40")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["LIBHPDF_SHARED"] = self.options.shared
        tc.variables["LIBHPDF_STATIC"] = not self.options.shared
        # Honor BUILD_SHARED_LIBS from conan_toolchain (see https://github.com/conan-io/conan/issues/11840)
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0077"] = "NEW"
        tc.generate()
        tc = CMakeDeps(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _v230_extract_license(self):
        readme = load(save, os.path.join(self.source_folder, "README"))
        match = next(re.finditer("\n[^\n]*license[^\n]*\n", readme, flags=re.I | re.A))
        return readme[match.span()[1]:].strip("*").strip()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        if Version(self.version) == "2.3.0":
            rm(self, "CHANGES", self.package_folder)
            rm(self, "INSTALL", self.package_folder)
            rm(self, "README", self.package_folder)

            rmdir(self, os.path.join(self.package_folder, "if"))
            save(self, os.path.join(self.package_folder, "licenses", "LICENSE"), self._v230_extract_license())
        else:
            copy(self, pattern="LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
            rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        libprefix = ""
        libsuffix = ""
        if Version(self.version) == "2.3.0":
            libprefix = "lib" if is_msvc(self) else ""
            libsuffix = "{}{}".format(
                "" if self.options.shared else "s",
                "d" if is_msvc(self) and self.settings.build_type == "Debug" else "",
            )
        self.cpp_info.libs = [f"{libprefix}hpdf{libsuffix}"]
        if self.settings.os == "Windows" and self.options.shared:
            self.cpp_info.defines = ["HPDF_DLL"]
        if self.settings.os in ["Linux", "FreeBSD"] and not self.options.shared:
            self.cpp_info.system_libs = ["m"]
