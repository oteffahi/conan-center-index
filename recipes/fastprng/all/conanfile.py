from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.layout import basic_layout
from conan.tools.files import get, copy
import os

required_conan_version = ">=1.52.0"


class FastPRNGConan(ConanFile):
    name = "fastprng"
    description = (
        "FAST 32/64 bit PRNG (pseudo-random generator), highly optimized, "
        "based on xoshiro* / xoroshiro*, xorshift and other Marsaglia algorithms."
    )
    license = "BSD-2-Clause"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/BrutPitt/fastPRNG"
    topics = ("random", "prng", "xorshift", "xoshiro", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def package_id(self):
        self.info.clear()

    def validate(self):
        if self.settings.get_safe("compiler.cppstd"):
            check_min_cppstd(self, "11")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        copy(self, "*.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "license.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
