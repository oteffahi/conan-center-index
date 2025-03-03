from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=1.52.0"


class MioConan(ConanFile):
    name = "mio"
    description = "Cross-platform C++11 header-only library for memory mapped file IO."
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/mandreyel/mio"
    topics = ("mmap", "memory-mapping", "fileviewer", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        for p in self.conan_data.get("patches", {}).get(self.version, []):
            copy(self, p["patch_file"], src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "*pp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mio")
        self.cpp_info.set_property("cmake_target_name", "mio::mio")
        self.cpp_info.bindirs = []
        self.cpp_info.frameworkdirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = []

        self.cpp_info.components["mio-headers"].set_property("cmake_target_name", "mio::mio-headers")
        self.cpp_info.components["mio-headers"].bindirs = []
        self.cpp_info.components["mio-headers"].frameworkdirs = []
        self.cpp_info.components["mio-headers"].libdirs = []
        self.cpp_info.components["mio-headers"].resdirs = []

        if self.settings.os == "Windows":
            self.cpp_info.components["mio_full_winapi"].set_property(
                "cmake_target_name", "mio::mio_full_winapi"
            )
            self.cpp_info.components["mio_full_winapi"].bindirs = []
            self.cpp_info.components["mio_full_winapi"].frameworkdirs = []
            self.cpp_info.components["mio_full_winapi"].libdirs = []
            self.cpp_info.components["mio_full_winapi"].resdirs = []

            self.cpp_info.components["mio_min_winapi"].set_property(
                "cmake_target_name", "mio::mio_min_winapi"
            )
            self.cpp_info.components["mio_min_winapi"].defines = ["WIN32_LEAN_AND_MEAN", "NOMINMAX"]
            self.cpp_info.components["mio_min_winapi"].bindirs = []
            self.cpp_info.components["mio_min_winapi"].frameworkdirs = []
            self.cpp_info.components["mio_min_winapi"].libdirs = []
            self.cpp_info.components["mio_min_winapi"].resdirs = []
