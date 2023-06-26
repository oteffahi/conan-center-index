# Warnings:
#   Unexpected method '_aes_defs'

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
import os

required_conan_version = ">=1.53.0"


class TinyAesCConan(ConanFile):
    name = "tiny-aes-c"
    description = "Small portable AES128/192/256 in C"
    license = "Unlicense"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/kokke/tiny-AES-c"
    topics = ("encryption", "crypto", "AES")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "aes_block_size": ["aes128", "aes192", "aes256"],
        "cbc": [True, False],
        "ecb": [True, False],
        "ctr": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "aes_block_size": "aes128",
        "cbc": True,
        "ecb": True,
        "ctr": True,
    }

    @property
    def _aes_defs(self):
        return {
            str(self.options.aes_block_size).upper(): "1",
            "CBC": "1" if self.options.cbc else "0",
            "ECB": "1" if self.options.ecb else "0",
            "CTR": "1" if self.options.ctr else "0",
        }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def validate(self):
        if not self.info.options.cbc and not self.info.options.ecb and not self.info.options.ctr:
            raise ConanInvalidConfiguration("Need to at least specify one of CBC, ECB or CTR modes")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        for definition, value in self._aes_defs.items():
            tc.preprocessor_definitions[definition] = value
        # Export symbols for shared msvc
        tc.variables["CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS"] = True
        # Relocatable shared lib on macOS
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        copy(self, "unlicense.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["tiny-aes"]
        self.cpp_info.defines.extend(
            [f"{definition}={value}" for definition, value in self._aes_defs.items()]
        )
