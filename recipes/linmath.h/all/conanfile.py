from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=1.50.0"


class LinmathConan(ConanFile):
    name = "linmath.h"
    description = (
        "A lean linear math library, aimed at graphics programming. Supports "
        "vec3, vec4, mat4x4 and quaternions"
    )
    license = "WTFPL"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/datenwolf/linmath.h"
    topics = ("math", "graphics", "linear-algebra", "vector", "matrix", "quaternion", "header-only")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        pass

    def package(self):
        copy(self, "LICENCE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "linmath.h",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
