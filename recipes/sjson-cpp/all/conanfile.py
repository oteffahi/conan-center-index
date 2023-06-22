from conans import ConanFile, tools
import os

required_conan_version = ">=1.33.0"


class SjsonCppConan(ConanFile):
    name = "sjson-cpp"
    description = "An Simplified JSON (SJSON) C++ reader and writer"
    topics = ("json", "sjson", "simplified")
    license = "MIT"
    homepage = "https://github.com/nfrechette/sjson-cpp"
    url = "https://github.com/conan-io/conan-center-index"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def package_id(self):
        self.info.header_only()

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            tools.check_min_cppstd(self, 11)

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], destination=self._source_subfolder, strip_root=True
        )

    def package(self):
        self.copy("LICENSE", dst="licenses", src=self._source_subfolder)
        self.copy("*.h", dst="include", src=os.path.join(self._source_subfolder, "includes"))
