# TODO: verify the Conan v2 migration

import os

from conan import ConanFile, conan_version
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.android import android_abi
from conan.tools.apple import (
    XCRun,
    fix_apple_shared_install_name,
    is_apple_os,
    to_apple_arch,
)
from conan.tools.build import (
    build_jobs,
    can_run,
    check_min_cppstd,
    cross_building,
    default_cppstd,
    stdcpp_library,
    valid_min_cppstd,
)
from conan.tools.cmake import (
    CMake,
    CMakeDeps,
    CMakeToolchain,
    cmake_layout,
)
from conan.tools.env import (
    Environment,
    VirtualBuildEnv,
    VirtualRunEnv,
)
from conan.tools.files import (
    apply_conandata_patches,
    chdir,
    collect_libs,
    copy,
    download,
    export_conandata_patches,
    get,
    load,
    mkdir,
    patch,
    patches,
    rename,
    replace_in_file,
    rm,
    rmdir,
    save,
    symlinks,
    unzip,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfig,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain, Meson
from conan.tools.microsoft import (
    MSBuild,
    MSBuildDeps,
    MSBuildToolchain,
    NMakeDeps,
    NMakeToolchain,
    VCVars,
    check_min_vs,
    is_msvc,
    is_msvc_static_runtime,
    msvc_runtime_flag,
    unix_path,
    unix_path_package_info_legacy,
    vs_layout,
)
from conan.tools.scm import Version
from conan.tools.system import package_manager
import conan.tools.files
import textwrap, shutil
import functools

required_conan_version = ">=1.53.0"


class ogrecmakeconan(ConanFile):
    name = "ogre"
    description = "A scene-oriented, flexible 3D engine written in C++ "
    license = "MIT"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/OGRECave/ogre"
    topics = ("graphics", "rendering", "engine", "c++")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "cp_bin_dir": "ANY",
        "cp_media_dir": "ANY",
        "disable_plugins": [True, False],
        "assert_mode": "ANY",
        "build_component_bites": [True, False],
        "build_component_hlms": [True, False],
        "build_component_meshlodgenerator": [True, False],
        "build_component_overlay": [True, False],
        "build_component_paging": [True, False],
        "build_component_property": [True, False],
        "build_component_python": [True, False],
        "build_component_rtshadersystem": [True, False],
        "build_component_terrain": [True, False],
        "build_component_volume": [True, False],
        "build_dependencies": [True, False],
        "build_plugin_bsp": [True, False],
        "build_plugin_octree": [True, False],
        "build_plugin_pcz": [True, False],
        "build_plugin_pfx": [True, False],
        "build_rendersystem_d3d11": [True, False],
        "build_rendersystem_gl": [True, False],
        "build_rendersystem_gl3plus": [True, False],
        "build_samples": [True, False],
        "build_tests": [True, False],
        "build_tools": [True, False],
        "config_enable_quad_buffer_stereo": [True, False],
        "config_filesystem_unicode": [True, False],
        "config_threads": "ANY",
        "config_thread_provider": "ANY",
        "config_enable_freeimage": [True, False],
        "install_pdb": [True, False],
        "install_samples": [True, False],
        "install_tools": [True, False],
        "install_vsprops": [True, False],
        "resourcemanager_strict": "ANY",
        "set_double": [True, False],
        "glsupport_use_egl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "cp_bin_dir": "bin",
        "cp_media_dir": "Media",
        "disable_plugins": False,
        "assert_mode": 1,
        "build_component_bites": True,
        "build_component_hlms": True,
        "build_component_meshlodgenerator": True,
        "build_component_overlay": True,
        "build_component_paging": True,
        "build_component_property": True,
        "build_component_python": False,
        "build_component_rtshadersystem": True,
        "build_component_terrain": True,
        "build_component_volume": True,
        "build_dependencies": False,
        "build_plugin_bsp": True,
        "build_plugin_octree": True,
        "build_plugin_pcz": True,
        "build_plugin_pfx": True,
        "build_rendersystem_d3d11": True,
        "build_rendersystem_gl": True,
        "build_rendersystem_gl3plus": True,
        "build_samples": False,
        "build_tests": False,
        "build_tools": True,
        "config_enable_quad_buffer_stereo": False,
        "config_filesystem_unicode": True,
        "config_threads": 3,
        "config_thread_provider": "std",
        "config_enable_freeimage": True,
        "install_pdb": False,
        "install_samples": False,
        "install_tools": False,
        "install_vsprops": False,
        "resourcemanager_strict": 2,
        "set_double": False,
        "glsupport_use_egl": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        self.options.install_tools = self.options.build_tools
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self._strict_options_requirements()

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("cppunit/1.15.1")
        self.requires("freeimage/3.18.0")
        self.requires("boost/1.83.0")
        self.requires("openexr/3.1.9")
        self.requires("freetype/2.13.0")
        self.requires("poco/1.12.4")
        self.requires("tbb/2020.3")
        self.requires("zlib/1.3")
        self.requires("zziplib/0.13.72")
        self.requires("openssl/[>=1.1 <4]", override=True)
        self.requires("xorg/system")
        self.requires("glu/system")
        self.requires("sdl/2.28.2")
        if self.options.glsupport_use_egl and self.settings.os in ["Linux", "FreeBSD"]:
            self.requires("egl/system")
        else:
            self.requires("libglvnd/1.5.0")

    def validate(self):
        """
        OGRE 1.x is very old and will not work with latest gcc, clang and msvc compilers.
        TODO: determine incompatible msvc compilers
        """
        if self.settings.compiler == "gcc" and Version(self.settings.compiler.version) >= 11:
            raise ConanInvalidConfiguration("OGRE 1.x not supported with gcc version greater than 11")
        if self.settings.compiler == "clang" and Version(self.settings.compiler.version) >= 11:
            raise ConanInvalidConfiguration("OGRE 1.x not supported with clang version greater than 11")

        miss_boost_required_comp = any(
            self.dependencies["boost"].options.get_safe(f"without_{boost_comp}", True)
            for boost_comp in self._required_boost_components
        )
        if self.dependencies["boost"].options.header_only or miss_boost_required_comp:
            raise ConanInvalidConfiguration(
                "OGRE requires these boost components: {}".format(", ".join(self._required_boost_components))
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _strict_options_requirements(self):
        self.options["boost"].header_only = False
        for boost_comp in self._required_boost_components:
            setattr(self.options["boost"], f"without_{boost_comp}", False)

    @property
    def _required_boost_components(self):
        return ["date_time", "thread"]

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OGRE_STATIC"] = not self.options.shared
        tc.variables["OGRE_CONFIG_DOUBLE"] = self.options.set_double
        tc.variables["OGRE_CONFIG_NODE_INHERIT_TRANSFORM"] = False
        tc.variables["OGRE_GLSUPPORT_USE_EGL"] = self.options.glsupport_use_egl
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)
        else:
            # INFO: OpenEXR requires C++11
            tc.variables["CMAKE_CXX_STANDARD"] = 11
        tc.variables["OGRE_BUILD_TESTS"] = self.options.build_tests
        tc.variables["OGRE_ASSERT_MODE"] = self.options.assert_mode
        tc.variables["OGRE_BUILD_COMPONENT_BITES"] = self.options.build_component_bites
        tc.variables["OGRE_BUILD_COMPONENT_HLMS"] = self.options.build_component_hlms
        tc.variables["OGRE_BUILD_COMPONENT_MESHLODGENERATOR"] = self.options.build_component_meshlodgenerator
        tc.variables["OGRE_BUILD_COMPONENT_OVERLAY"] = self.options.build_component_overlay
        tc.variables["OGRE_BUILD_COMPONENT_PAGING"] = self.options.build_component_paging
        tc.variables["OGRE_BUILD_COMPONENT_PROPERTY"] = self.options.build_component_property
        tc.variables["OGRE_BUILD_COMPONENT_PYTHON"] = self.options.build_component_python
        tc.variables["OGRE_BUILD_COMPONENT_RTSHADERSYSTEM"] = self.options.build_component_rtshadersystem
        tc.variables["OGRE_BUILD_COMPONENT_TERRAIN"] = self.options.build_component_terrain
        tc.variables["OGRE_BUILD_COMPONENT_VOLUME"] = self.options.build_component_volume
        tc.variables["OGRE_BUILD_DEPENDENCIES"] = self.options.build_dependencies
        tc.variables["OGRE_BUILD_PLUGIN_BSP"] = self.options.build_plugin_bsp
        tc.variables["OGRE_BUILD_PLUGIN_OCTREE"] = self.options.build_plugin_octree
        tc.variables["OGRE_BUILD_PLUGIN_PCZ"] = self.options.build_plugin_pcz
        tc.variables["OGRE_BUILD_PLUGIN_PFX"] = self.options.build_plugin_pfx
        tc.variables["OGRE_BUILD_RENDERSYSTEM_D3D11"] = self.options.build_rendersystem_d3d11
        tc.variables["OGRE_BUILD_RENDERSYSTEM_GL"] = self.options.build_rendersystem_gl
        tc.variables["OGRE_BUILD_RENDERSYSTEM_GL3PLUS"] = self.options.build_rendersystem_gl3plus
        tc.variables["OGRE_BUILD_SAMPLES"] = self.options.build_samples
        tc.variables["OGRE_BUILD_TOOLS"] = self.options.build_tools
        tc.variables["OGRE_CONFIG_ENABLE_QUAD_BUFFER_STEREO"] = self.options.config_enable_quad_buffer_stereo
        tc.variables["OGRE_CONFIG_FILESYSTEM_UNICODE"] = self.options.config_filesystem_unicode
        tc.variables["OGRE_CONFIG_THREADS"] = self.options.config_threads
        tc.variables["OGRE_CONFIG_THREAD_PROVIDER"] = self.options.config_thread_provider
        tc.variables["OGRE_CONFIG_ENABLE_FREEIMAGE"] = self.options.config_enable_freeimage
        tc.variables["OGRE_INSTALL_PDB"] = self.options.install_pdb
        tc.variables["OGRE_INSTALL_SAMPLES"] = self.options.install_samples
        tc.variables["OGRE_INSTALL_TOOLS"] = self.options.install_tools
        tc.variables["OGRE_RESOURCEMANAGER_STRICT"] = self.options.resourcemanager_strict
        if self.settings.os == "Windows":
            tc.variables["OGRE_INSTALL_VSPROPS"] = self.options.install_vsprops
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)
        # the pkgs below are not available as conan recipes yet
        # TODO: delte line 200-208 once the conan recipes are available
        ogre_pkg_modules = [
            "AMDQBS",
            "Cg",
            "HLSL2GLSL",
            "GLSLOptimizer",
            "OpenGLES",
            "OpenGLES2",
            "OpenGLES3",
            "SDL2",
            "Softimage",
            "Wix",
        ]
        ogre_pkg_module_path = os.path.join(self.build_folder, self.source_folder, "CMake", "Packages")
        for pkg_module in ogre_pkg_modules:
            pkg_path = os.path.join(ogre_pkg_module_path, f"Find{pkg_module}.cmake")
            if os.path.isfile(pkg_path):
                shutil.copy(pkg_path, self.build_folder)
            else:
                raise ConanException(
                    f"The file Find{pkg_module}.cmake is not present in f{ogre_pkg_module_path}!"
                )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _create_cmake_module_variables(self, module_file, version):
        content = textwrap.dedent(f"""\
            set(OGRE_PREFIX_DIR ${{CMAKE_CURRENT_LIST_DIR}}/../..)
            set(OGRE{version.major}_VERSION_MAJOR {version.major})
            set(OGRE{version.major}_VERSION_MINOR {version.minor})
            set(OGRE{version.major}_VERSION_PATCH {version.patch})
            set(OGRE{version.major}_VERSION_STRING "{version.major}.{version.minor}.{version.patch}")

            set(OGRE_MEDIA_DIR "${{OGRE_PREFIX_DIR}}/share/OGRE/Media")
            set(OGRE_PLUGIN_DIR "${{OGRE_PREFIX_DIR}}/lib/OGRE")
            set(OGRE_CONFIG_DIR "${{OGRE_PREFIX_DIR}}/share/OGRE")
        """)
        save(self, module_file, content)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "License.md",
             dst=os.path.join(self.package_folder, "licenses"),
             src=os.path.join(self.source_folder, "Docs"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "OGRE", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        self._create_cmake_module_variables(
            os.path.join(self.package_folder, self._module_file_rel_path), Version(self.version)
        )

    @property
    def _components(self):
        include_prefix = os.path.join("include", "OGRE")
        plugin_lib_dir = os.path.join("lib", "OGRE")
        components = {
            "OgreMain": {
                "requires": [
                    "boost::boost",
                    "cppunit::cppunit",
                    "freeimage::freeimage",
                    "openexr::openexr",
                    "freetype::freetype",
                    "sdl::sdl",
                    "tbb::tbb",
                    "xorg::xorg",
                    "zlib::zlib",
                    "zziplib::zziplib",
                    "poco::poco",
                    "glu::glu",
                    "egl::egl",
                ],
                "libs": ["OgreMain"],
                "include": [include_prefix],
                "libdirs": ["lib"],
            },
            "Bites": {
                "requires": ["OgreMain", "Overlay"],
                "libs": ["OgreBites"],
                "include": ["include", include_prefix, f"{include_prefix}/Bites"],
                "libdirs": ["lib"],
            },
            "HLMS": {
                "requires": ["OgreMain"],
                "libs": ["OgreHLMS"],
                "include": ["include", include_prefix, f"{include_prefix}/HLMS"],
                "libdirs": ["lib"],
            },
            "MeshLodGenerator": {
                "requires": ["OgreMain"],
                "libs": ["OgreMeshLodGenerator"],
                "include": ["include", include_prefix, f"{include_prefix}/MeshLodGenerator"],
                "libdirs": ["lib"],
            },
            "Overlay": {
                "requires": ["OgreMain"],
                "libs": ["OgreOverlay"],
                "include": ["include", include_prefix, f"{include_prefix}/Overlay"],
                "libdirs": ["lib"],
            },
            "Paging": {
                "requires": ["OgreMain"],
                "libs": ["OgrePaging"],
                "include": ["include", include_prefix, f"{include_prefix}/Paging"],
                "libdirs": ["lib"],
            },
            "Property": {
                "requires": ["OgreMain"],
                "libs": ["OgreProperty"],
                "include": ["include", include_prefix, f"{include_prefix}/Property"],
                "libdirs": ["lib"],
            },
            "RTShaderSystem": {
                "requires": ["OgreMain"],
                "libs": ["OgreRTShaderSystem"],
                "include": ["include", include_prefix, f"{include_prefix}/RTShaderSystem"],
                "libdirs": ["lib"],
            },
            "Terrain": {
                "requires": ["OgreMain"],
                "libs": ["OgreTerrain"],
                "include": ["include", include_prefix, f"{include_prefix}/Terrain"],
                "libdirs": ["lib"],
            },
            "Volume": {
                "requires": ["OgreMain"],
                "libs": ["OgreVolume"],
                "include": ["include", include_prefix, f"{include_prefix}/Volume"],
                "libdirs": ["lib"],
            },
        }

        if self.options.build_component_python:
            components["Python"] = {
                "requires": ["OgreMain"],
                "libs": ["OgrePython"],
                "include": ["include", include_prefix, f"{include_prefix}/Python"],
            }

        if self.options.build_plugin_bsp:
            components["BSPSceneManager"] = {
                "requires": ["OgreMain"],
                "libs": ["Plugin_BSPSceneManager"],
                "libdirs": ["lib", plugin_lib_dir],
                "include": [
                    "include",
                    include_prefix,
                    os.path.join(include_prefix, "Plugins", "BSPSceneManager"),
                ],
            }

        if self.options.build_plugin_octree:
            components["OctreeSceneManager"] = {
                "requires": ["OgreMain"],
                "libs": ["Plugin_OctreeSceneManager"],
                "libdirs": ["lib", plugin_lib_dir],
                "include": [
                    "include",
                    include_prefix,
                    os.path.join(include_prefix, "Plugins", "OctreeSceneManager"),
                ],
            }

        if self.options.build_plugin_pfx:
            components["ParticleFX"] = {
                "requires": ["OgreMain"],
                "libs": ["Plugin_ParticleFX"],
                "libdirs": ["lib", plugin_lib_dir],
                "include": ["include", include_prefix, os.path.join(include_prefix, "Plugins", "ParticleFX")],
            }

        if self.options.build_plugin_pcz:
            components["PCZSceneManager"] = {
                "requires": ["OgreMain"],
                "libs": ["Plugin_PCZSceneManager"],
                "libdirs": ["lib", plugin_lib_dir],
                "include": [
                    "include",
                    include_prefix,
                    os.path.join(include_prefix, "Plugins", "PCZSceneManager"),
                ],
            }

            components["OctreeZone"] = {
                "requires": ["OgreMain", "PCZSceneManager"],
                "libs": ["Plugin_OctreeZone"],
                "libdirs": ["lib", plugin_lib_dir],
                "include": ["include", include_prefix, os.path.join(include_prefix, "Plugins", "OctreeZone")],
            }

        if not self.options.shared:
            for _, values in components.items():
                libs = [lib + "Static" for lib in values.get("libs")]
                values["libs"] = libs

        if self.options.build_tests:
            components["OgreMain"]["requires"].append("cppunit::cppunit")

        if self.settings.build_type == "Debug":
            for _, values in components.items():
                libs = [lib + "_d" for lib in values.get("libs")]
                values["libs"] = libs

        return components

    @property
    def _module_file_rel_dir(self):
        return os.path.join("lib", "cmake")

    @property
    def _module_file_rel_path(self):
        return os.path.join(self._module_file_rel_dir, f"conan-official-{self.name}-variables.cmake")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OGRE")
        self.cpp_info.names["cmake_find_package"] = "OGRE"
        self.cpp_info.names["cmake_find_package_multi"] = "OGRE"

        for comp, values in self._components.items():
            self.cpp_info.components[comp].names["cmake_find_package"] = comp
            self.cpp_info.components[comp].names["cmake_find_package_multi"] = comp
            self.cpp_info.components[comp].names["cmake_paths"] = comp
            self.cpp_info.components[comp].libs = values.get("libs")
            self.cpp_info.components[comp].libdirs = values.get("libdirs")
            self.cpp_info.components[comp].requires = values.get("requires")
            self.cpp_info.components[comp].set_property("cmake_target_name", f"OGRE::{comp}")
            self.cpp_info.components[comp].includedirs = values.get("include")

            self.cpp_info.components[comp].builddirs.append(self._module_file_rel_dir)
            self.cpp_info.components[comp].build_modules["cmake_find_package"] = [self._module_file_rel_path]
            self.cpp_info.components[comp].build_modules["cmake_find_package_multi"] = [
                self._module_file_rel_path
            ]
            self.cpp_info.components[comp].build_modules["cmake_paths"] = [self._module_file_rel_path]
            self.cpp_info.components[comp].builddirs.append(self._module_file_rel_path)
            if self.settings.os in ["Linux", "FreeBSD"]:
                self.cpp_info.components[comp].system_libs.append("pthread")

        if self.options.install_tools:
            self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
