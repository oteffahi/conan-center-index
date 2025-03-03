import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMakeToolchain, CMake, CMakeDeps, cmake_layout
from conan.tools.files import copy, get
from conan.tools.microsoft import is_msvc

required_conan_version = ">=1.53.0"


class TheoraConan(ConanFile):
    name = "theora"
    description = "Theora is a free and open video compression format from the Xiph.org Foundation"
    license = "BSD-3-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/xiph/theora"
    topics = ("video", "video-compressor", "video-format")

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
        copy(self, "CMakeLists.txt",
             src=self.recipe_folder,
             dst=os.path.join(self.export_sources_folder, "src"))

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            try:
                self.options.rm_safe("fPIC")
            except ConanException:
                pass
        try:
            self.settings.rm_safe("compiler.libcxx")
        except ConanException:
            pass
        try:
            self.settings.rm_safe("compiler.cppstd")
        except ConanException:
            pass

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("ogg/1.3.5")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["USE_X86_32"] = self.settings.arch == "x86"
        # note: MSVC does not support inline assembly for 64 bit builds
        tc.variables["USE_X86_64"] = self.settings.arch == "x86_64" and not is_msvc(self)
        tc.generate()
        cd = CMakeDeps(self)
        cd.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure(build_script_folder=self.source_path.parent)
        cmake.build()

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property(
            "pkg_config_name", "theora_full_package_do_not_use"
        )  # to avoid conflicts with theora component

        self.cpp_info.components["theora"].set_property("pkg_config_name", "theora")
        self.cpp_info.components["theora"].libs = ["theora"]
        self.cpp_info.components["theora"].requires = ["ogg::ogg"]

        self.cpp_info.components["theoradec"].set_property("pkg_config_name", "theoradec")
        self.cpp_info.components["theoradec"].libs = ["theoradec"]
        self.cpp_info.components["theoradec"].requires = ["ogg::ogg"]

        self.cpp_info.components["theoraenc"].set_property("pkg_config_name", "theoraenc")
        self.cpp_info.components["theoraenc"].libs = ["theoraenc"]
        self.cpp_info.components["theoraenc"].requires = ["ogg::ogg"]
