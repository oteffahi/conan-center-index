from conans import ConanFile, tools
import os


class TypeSafe(ConanFile):
    name = "fff"
    description = "A testing micro framework for creating function test doubles"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/meekrosoft/fff"
    license = "MIT"
    topics = ("c", "c++", "embedded", "tdd", "micro-framework", "fake-functions")

    no_copy_source = True

    def source(self):
        tools.get(
            **self.conan_data["sources"][self.version], strip_root=True, destination=self._source_subfolder
        )

    def package(self):
        self.copy("LICENSE*", dst="licenses", src=self._source_subfolder)
        self.copy("fff.h", dst="include", src=self._source_subfolder)

    def package_id(self):
        self.info.header_only()
