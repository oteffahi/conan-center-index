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
import functools
import json
import os
import textwrap

required_conan_version = ">=1.53.0"


class OpenCascadeConan(ConanFile):
    name = "opencascade"
    description = (
        "A software development platform providing services for 3D "
        "surface and solid modeling, CAD data exchange, and visualization."
    )
    license = "LGPL-2.1-or-later"
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://dev.opencascade.org"
    topics = ("occt", "3d", "modeling", "cad")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_ffmpeg": [True, False],
        "with_freeimage": [True, False],
        "with_openvr": [True, False],
        "with_rapidjson": [True, False],
        "with_draco": [True, False],
        "with_tk": [True, False],
        "with_tbb": [True, False],
        "with_opengl": [True, False],
        "extended_debug_messages": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_ffmpeg": False,
        "with_freeimage": False,
        "with_openvr": False,
        "with_rapidjson": False,
        "with_draco": False,
        "with_tk": True,
        "with_tbb": False,
        "with_opengl": True,
        "extended_debug_messages": False,
    }

    @property
    def _is_linux(self):
        return self.settings.os in ["Linux", "FreeBSD"]

    @property
    def _link_tk(self):
        if Version(self.version) >= "7.6.0":
            return self.options.with_tk
        else:
            return True

    @property
    def _link_opengl(self):
        if Version(self.version) >= "7.6.0":
            return self.options.with_opengl
        else:
            return True

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if Version(self.version) < "7.6.0":
            self.options.rm_safe("with_tk")
            self.options.rm_safe("with_draco")
            self.options.rm_safe("with_opengl")
        if self.settings.os == "Windows":
            del self.options.fPIC
        if self.settings.build_type != "Debug":
            self.options.rm_safe("extended_debug_messages")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        self.requires("tcl/8.6.11")
        if self._link_tk:
            self.requires("tk/8.6.10")
        self.requires("freetype/2.13.0")
        if self._link_opengl:
            self.requires("opengl/system")
        if self._is_linux:
            self.requires("fontconfig/2.14.2")
            self.requires("xorg/system")
        # TODO: add vtk support?
        if self.options.with_ffmpeg:
            self.requires("ffmpeg/6.0")
        if self.options.with_freeimage:
            self.requires("freeimage/3.18.0")
        if self.options.with_openvr:
            self.requires("openvr/1.16.8")
        if self.options.with_rapidjson:
            self.requires("rapidjson/cci.20220822")
        if self.options.get_safe("with_draco"):
            self.requires("draco/1.5.6")
        if self.options.with_tbb:
            self.requires("onetbb/2021.9.0")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)
        if (
            self.settings.compiler == "clang"
            and self.settings.compiler.version == "6.0"
            and self.settings.build_type == "Release"
        ):
            raise ConanInvalidConfiguration(
                "OpenCASCADE {} doesn't support Clang 6.0 if Release build type".format(self.version)
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # Inject C++ standard from profile since we have removed hardcoded C++11 from upstream build files
        if not valid_min_cppstd(self, 11):
            tc.variables["CMAKE_CXX_STANDARD"] = 11

        # Generate a relocatable shared lib on Macos
        tc.variables["CMAKE_POLICY_DEFAULT_CMP0042"] = "NEW"

        tc.variables["BUILD_LIBRARY_TYPE"] = "Shared" if self.options.shared else "Static"
        tc.variables["INSTALL_TEST_CASES"] = False
        tc.variables["BUILD_RESOURCES"] = False
        tc.variables["BUILD_RELEASE_DISABLE_EXCEPTIONS"] = True
        if self.settings.build_type == "Debug":
            tc.variables["BUILD_WITH_DEBUG"] = self.options.extended_debug_messages
        tc.variables["BUILD_USE_PCH"] = False
        tc.variables["INSTALL_SAMPLES"] = False

        tc.variables["INSTALL_DIR_LAYOUT"] = "Unix"
        tc.variables["INSTALL_DIR_BIN"] = "bin"
        tc.variables["INSTALL_DIR_LIB"] = "lib"
        tc.variables["INSTALL_DIR_INCLUDE"] = "include"
        tc.variables["INSTALL_DIR_RESOURCE"] = "res/resource"
        tc.variables["INSTALL_DIR_DATA"] = "res/data"
        tc.variables["INSTALL_DIR_SAMPLES"] = "res/samples"
        tc.variables["INSTALL_DIR_DOC"] = "res/doc"

        if is_msvc(self):
            tc.variables["BUILD_SAMPLES_MFC"] = False
        tc.variables["BUILD_SAMPLES_QT"] = False
        tc.variables["BUILD_Inspector"] = False
        if is_apple_os(self):
            tc.variables["USE_GLX"] = False
        if self.settings.os == "Windows":
            tc.variables["USE_D3D"] = False
        tc.variables["BUILD_ENABLE_FPE_SIGNAL_HANDLER"] = False
        tc.variables["BUILD_DOC_Overview"] = False

        tc.variables["USE_FREEIMAGE"] = self.options.with_freeimage
        tc.variables["USE_OPENVR"] = self.options.with_openvr
        tc.variables["USE_FFMPEG"] = self.options.with_ffmpeg
        tc.variables["USE_TBB"] = self.options.with_tbb
        tc.variables["USE_RAPIDJSON"] = self.options.with_rapidjson
        if Version(self.version) >= "7.6.0":
            tc.variables["USE_DRACO"] = self.options.with_draco
            tc.variables["USE_TK"] = self.options.with_tk
            tc.variables["USE_OPENGL"] = self.options.with_opengl
        tc.generate()

        tc = CMakeDeps(self)
        tc.generate()

    def _patch_sources(self):
        apply_conandata_patches(self)

        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        cmakelists_tools = os.path.join(self.source_folder, "tools", "CMakeLists.txt")
        occt_toolkit_cmake = os.path.join(self.source_folder, "adm", "cmake", "occt_toolkit.cmake")
        occt_csf_cmake = os.path.join(self.source_folder, "adm", "cmake", "occt_csf.cmake")
        occt_defs_flags_cmake = os.path.join(self.source_folder, "adm", "cmake", "occt_defs_flags.cmake")

        # Inject conanbuildinfo, upstream build files are not ready for a CMake wrapper (too much modifications required)
        # Also inject compile flags
        replace_in_file(
            self,
            cmakelists,
            "project (OCCT)",
            (
                "project (OCCT)\n"
                "include(${CMAKE_BINARY_DIR}/conanbuildinfo.cmake)\n"
                "conan_basic_setup(TARGETS KEEP_RPATHS)\n"
                "conan_global_flags()"
            ),
        )

        # Avoid to add system include/libs directories
        replace_in_file(self, cmakelists, "3RDPARTY_INCLUDE_DIRS", "CONAN_INCLUDE_DIRS")
        replace_in_file(self, cmakelists, "3RDPARTY_LIBRARY_DIRS", "CONAN_LIB_DIRS")
        replace_in_file(self, cmakelists_tools, "3RDPARTY_INCLUDE_DIRS", "CONAN_INCLUDE_DIRS")
        replace_in_file(self, cmakelists_tools, "3RDPARTY_LIBRARY_DIRS", "CONAN_LIB_DIRS")

        # Do not fail due to "fragile" upstream logic to find dependencies
        replace_in_file(self, cmakelists, "if (3RDPARTY_NOT_INCLUDED)", "if(0)")
        replace_in_file(self, cmakelists, "if (3RDPARTY_NO_LIBS)", "if(0)")
        replace_in_file(self, cmakelists, "if (3RDPARTY_NO_DLLS)", "if(0)")

        # Inject dependencies from conan, and avoid to rely on upstream custom CMake files
        conan_targets = []

        ## freetype
        conan_targets.append("CONAN_PKG::freetype")
        replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/freetype")', "")
        replace_in_file(
            self,
            occt_csf_cmake,
            'set (CSF_FREETYPE "freetype")',
            'set (CSF_FREETYPE "{}")'.format(" ".join(self.dependencies["freetype"].cpp_info.libs)),
        )
        ## tcl
        conan_targets.append("CONAN_PKG::tcl")
        replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/tcl")', "")
        csf_tcl_libs = 'set (CSF_TclLibs "{}")'.format(" ".join(self.dependencies["tcl"].cpp_info.libs))
        replace_in_file(self, occt_csf_cmake, 'set (CSF_TclLibs     "tcl86")', csf_tcl_libs)
        replace_in_file(self, occt_csf_cmake, "set (CSF_TclLibs   Tcl)", csf_tcl_libs)
        if Version(self.version) >= "7.6.0":
            replace_in_file(self, occt_csf_cmake, 'set (CSF_TclLibs   "tcl8.6")', csf_tcl_libs)
        else:
            replace_in_file(self, occt_csf_cmake, 'set (CSF_TclLibs     "tcl8.6")', csf_tcl_libs)
        ## tk
        if self._link_tk:
            conan_targets.append("CONAN_PKG::tk")
            replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/tk")', "")
            csf_tk_libs = 'set (CSF_TclTkLibs "{}")'.format(" ".join(self.dependencies["tk"].cpp_info.libs))
            replace_in_file(self, occt_csf_cmake, 'set (CSF_TclTkLibs   "tk86")', csf_tk_libs)
            replace_in_file(self, occt_csf_cmake, "set (CSF_TclTkLibs Tk)", csf_tk_libs)
            if Version(self.version) >= "7.6.0":
                replace_in_file(self, occt_csf_cmake, 'set (CSF_TclTkLibs "tk8.6")', csf_tk_libs)
            else:
                replace_in_file(self, occt_csf_cmake, 'set (CSF_TclTkLibs   "tk8.6")', csf_tk_libs)
        ## fontconfig
        if self._is_linux:
            conan_targets.append("CONAN_PKG::fontconfig")
            if Version(self.version) >= "7.6.0":
                replace_in_file(
                    self,
                    occt_csf_cmake,
                    'set (CSF_fontconfig "fontconfig")',
                    'set (CSF_fontconfig "{}")'.format(
                        " ".join(self.dependencies["fontconfig"].cpp_info.libs)
                    ),
                )
            else:
                replace_in_file(
                    self,
                    occt_csf_cmake,
                    'set (CSF_fontconfig  "fontconfig")',
                    'set (CSF_fontconfig  "{}")'.format(
                        " ".join(self.dependencies["fontconfig"].cpp_info.libs)
                    ),
                )
        ## onetbb
        if self.options.with_tbb:
            conan_targets.append("CONAN_PKG::onetbb")
            replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/tbb")', "")
            replace_in_file(
                self,
                occt_csf_cmake,
                'set (CSF_TBB "tbb tbbmalloc")',
                'set (CSF_TBB "{}")'.format(" ".join(self.dependencies["onetbb"].cpp_info.libs)),
            )
        ## ffmpeg
        if self.options.with_ffmpeg:
            conan_targets.append("CONAN_PKG::ffmpeg")
            replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/ffmpeg")', "")
            replace_in_file(
                self,
                occt_csf_cmake,
                'set (CSF_FFmpeg "avcodec avformat swscale avutil")',
                'set (CSF_FFmpeg "{}")'.format(" ".join(self.dependencies["ffmpeg"].cpp_info.libs)),
            )
        ## freeimage
        if self.options.with_freeimage:
            conan_targets.append("CONAN_PKG::freeimage")
            replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/freeimage")', "")
            replace_in_file(
                self,
                occt_csf_cmake,
                'set (CSF_FreeImagePlus "freeimage")',
                'set (CSF_FreeImagePlus "{}")'.format(" ".join(self.dependencies["freeimage"].cpp_info.libs)),
            )
        ## openvr
        if self.options.with_openvr:
            conan_targets.append("CONAN_PKG::openvr")
            replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/openvr")', "")
            replace_in_file(
                self,
                occt_csf_cmake,
                'set (CSF_OpenVR "openvr_api")',
                'set (CSF_OpenVR "{}")'.format(" ".join(self.dependencies["openvr"].cpp_info.libs)),
            )
        ## rapidjson
        if self.options.with_rapidjson:
            conan_targets.append("CONAN_PKG::rapidjson")
            replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/rapidjson")', "")
        ## draco
        if self.options.get_safe("with_draco"):
            conan_targets.append("CONAN_PKG::draco")
            replace_in_file(self, cmakelists, 'OCCT_INCLUDE_CMAKE_FILE ("adm/cmake/draco")', "")
        ## opengl
        replace_in_file(self, occt_csf_cmake, "set (CSF_OpenGlLibs ", "# set (CSF_OpenGlLibs ")
        if self._link_opengl:
            conan_targets.append("CONAN_PKG::opengl")

        ## Inject conan targets
        replace_in_file(
            self,
            occt_toolkit_cmake,
            "${USED_EXTERNAL_LIBS_BY_CURRENT_PROJECT}",
            "${{USED_EXTERNAL_LIBS_BY_CURRENT_PROJECT}} {}".format(" ".join(conan_targets)),
        )

        # Do not install pdb files
        if Version(self.version) >= "7.6.0":
            replace_in_file(
                self,
                occt_toolkit_cmake,
                """    install (FILES  ${CMAKE_BINARY_DIR}/${OS_WITH_BIT}/${COMPILER}/bin\\${OCCT_INSTALL_BIN_LETTER}/${PROJECT_NAME}.pdb
             CONFIGURATIONS Debug ${aReleasePdbConf} RelWithDebInfo
             DESTINATION "${INSTALL_DIR_BIN}\\${OCCT_INSTALL_BIN_LETTER}")""",
                "",
            )
        else:
            replace_in_file(
                self,
                occt_toolkit_cmake,
                """    install (FILES  ${CMAKE_BINARY_DIR}/${OS_WITH_BIT}/${COMPILER}/bin\\${OCCT_INSTALL_BIN_LETTER}/${PROJECT_NAME}.pdb
             CONFIGURATIONS Debug RelWithDebInfo
             DESTINATION "${INSTALL_DIR_BIN}\\${OCCT_INSTALL_BIN_LETTER}")""",
                "",
            )

        # Honor fPIC option, compiler.cppstd and compiler.libcxx
        replace_in_file(self, occt_defs_flags_cmake, "-fPIC", "")
        replace_in_file(self, occt_defs_flags_cmake, "-std=c++0x", "")
        replace_in_file(self, occt_defs_flags_cmake, "-std=gnu++0x", "")
        replace_in_file(self, occt_defs_flags_cmake, "-stdlib=libc++", "")
        replace_in_file(
            self,
            occt_csf_cmake,
            'set (CSF_ThreadLibs  "pthread rt stdc++")',
            'set (CSF_ThreadLibs  "pthread rt")',
        )

        # No hardcoded link through #pragma
        if Version(self.version) < "7.6.0":
            replace_in_file(
                self,
                os.path.join(self.source_folder, "src", "Font", "Font_FontMgr.cxx"),
                '#pragma comment (lib, "freetype.lib")',
                "",
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "src", "Draw", "Draw.cxx"),
                """#pragma comment (lib, "tcl" STRINGIZE2(TCL_MAJOR_VERSION) STRINGIZE2(TCL_MINOR_VERSION) ".lib")
#pragma comment (lib, "tk"  STRINGIZE2(TCL_MAJOR_VERSION) STRINGIZE2(TCL_MINOR_VERSION) ".lib")""",
                "",
            )

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _replace_package_folder(self, source, target):
        if os.path.isdir(os.path.join(self.package_folder, source)):
            rmdir(self, os.path.join(self.package_folder, target))
            rename(self, os.path.join(self.package_folder, source), os.path.join(self.package_folder, target))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE_LGPL_21.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "OCCT_LGPL_EXCEPTION.txt",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rmdir(self, os.path.join(self.package_folder, "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        if self.settings.build_type == "Debug":
            self._replace_package_folder("libd", "lib")
            self._replace_package_folder("bind", "bin")
        elif self.settings.build_type == "RelWithDebInfo":
            self._replace_package_folder("libi", "lib")
            self._replace_package_folder("bini", "bin")

        occt_modules = self._get_modules_from_source_code()
        self._create_modules_json_file(occt_modules)

        # TODO: to remove in conan v2 once cmake_find_package* generators removed
        self._create_cmake_module_alias_targets(
            os.path.join(self.package_folder, self._cmake_module_file_rel_path),
            {target: f"OpenCASCADE::{target}" for module in occt_modules.values() for target in module},
        )

    def _create_cmake_module_alias_targets(self, module_file, targets):
        content = ""
        for alias, aliased in targets.items():
            content += textwrap.dedent(f"""\
                if(TARGET {aliased} AND NOT TARGET {alias})
                    add_library({alias} INTERFACE IMPORTED)
                    set_property(TARGET {alias} PROPERTY INTERFACE_LINK_LIBRARIES {aliased})
                endif()
            """)
        save(self, module_file, content)

    @property
    def _cmake_module_file_rel_path(self):
        return os.path.join("lib", "cmake", "conan-official-{}-targets.cmake".format(self.name))

    def _get_modules_from_source_code(self):
        csf_to_conan_dependencies = {
            # Mandatory dependencies
            "CSF_FREETYPE": {"externals": ["freetype::freetype"]},
            "CSF_TclLibs": {"externals": ["tcl::tcl"]},
            "CSF_fontconfig": {"externals": ["fontconfig::fontconfig"] if self._is_linux else []},
            "CSF_XwLibs": {"externals": ["xorg::xorg"] if self._is_linux else []},
            # Optional dependencies
            "CSF_OpenGlLibs": {"externals": ["opengl::opengl"] if self._link_opengl else []},
            "CSF_TclTkLibs": {"externals": ["tk::tk"] if self._link_tk else []},
            "CSF_FFmpeg": {"externals": ["ffmpeg::ffmpeg"] if self.options.with_ffmpeg else []},
            "CSF_FreeImagePlus": {
                "externals": ["freeimage::freeimage"] if self.options.with_freeimage else []
            },
            "CSF_OpenVR": {"externals": ["openvr::openvr"] if self.options.with_openvr else []},
            "CSF_RapidJSON": {"externals": ["rapidjson::rapidjson"] if self.options.with_rapidjson else []},
            "CSF_Draco": {"externals": ["draco::draco"] if self.options.get_safe("with_draco") else []},
            "CSF_TBB": {"externals": ["onetbb::onetbb"] if self.options.with_tbb else []},
            "CSF_VTK": {},
            # Android system libs
            "CSF_androidlog": {"system_libs": ["log"] if self.settings.os == "Android" else []},
            # Linux system libs
            "CSF_ThreadLibs": {"system_libs": ["pthread", "rt"] if self._is_linux else []},
            "CSF_dl": {"system_libs": ["dl"] if self._is_linux else []},
            "CSF_dpsLibs": {},
            "CSF_XmuLibs": {},
            # Windows system libs
            "CSF_advapi32": {"system_libs": ["advapi32"] if self.settings.os == "Windows" else []},
            "CSF_gdi32": {"system_libs": ["gdi32"] if self.settings.os == "Windows" else []},
            "CSF_psapi": {"system_libs": ["psapi"] if self.settings.os == "Windows" else []},
            "CSF_shell32": {"system_libs": ["shell32"] if self.settings.os == "Windows" else []},
            "CSF_user32": {"system_libs": ["user32"] if self.settings.os == "Windows" else []},
            "CSF_winmm": {"system_libs": ["winmm"] if self.settings.os == "Windows" else []},
            "CSF_wsock32": {"system_libs": ["wsock32"] if self.settings.os == "Windows" else []},
            "CSF_d3d9": {},
            # Apple OS frameworks
            "CSF_Appkit": {
                "frameworks": (
                    ["UIKit"]
                    if self.settings.os == "iOS"
                    else ["Appkit"] if is_apple_os(self) else []
                )
            },
            "CSF_IOKit": {"frameworks": ["IOKit"] if is_apple_os(self) else []},
            "CSF_objc": {},
        }

        modules = {}

        # MODULES file lists all modules and all possible components per module
        modules_content = load(self, os.path.join(self.build_folder, self.source_folder, "adm", "MODULES"))
        packaged_libs_list = collect_libs(self, "lib")
        for module_line in modules_content.splitlines():
            components = {}
            module_components = module_line.split()
            components_list = [
                component for component in module_components[1:] if component in packaged_libs_list
            ]
            for component_name in components_list:
                component_deps = {}
                # EXTERNLIB file stores dependencies of each component. External dependencies are prefixed with CSF_
                externlib_content = load(
                    self,
                    os.path.join(self.build_folder, self.source_folder, "src", component_name, "EXTERNLIB"),
                )
                for dependency in externlib_content.splitlines():
                    if dependency.startswith("TK") and dependency in packaged_libs_list:
                        component_deps.setdefault("internals", []).append(dependency)
                    elif dependency.startswith("CSF_"):
                        deps_dict = csf_to_conan_dependencies[dependency]
                        for dep_type, deps in deps_dict.items():
                            if deps:
                                component_deps.setdefault(dep_type, []).extend(deps)
                components.update({component_name: component_deps})
            modules.update({module_components[0]: components})

        return modules

    def _create_modules_json_file(self, modules):
        save(self._modules_helper_filepath, json.dumps(modules, indent=4))

    @property
    def _modules_helper_filepath(self):
        return os.path.join(self.package_folder, "lib", "occt_modules.json")

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "OpenCASCADE")

        def _to_qualified_name(target):
            return "occt_{}".format(target.lower())

        def _register_components(modules_dict):
            for module, targets in modules_dict.items():
                conan_component_module_name = _to_qualified_name(module)
                # FIXME: in this "module" target we would like to model COMPONENTS for find_package() but
                #       for the moment it generates in CMakeDeps some weird component name like
                #       opencascade::FoundationClasses instead of FoundationClasses.
                #       see https://github.com/conan-io/conan/issues/10258
                self.cpp_info.components[conan_component_module_name].set_property(
                    "cmake_target_name", module
                )

                for target_lib, target_deps in targets.items():
                    conan_component_target_name = _to_qualified_name(target_lib)
                    requires = [_to_qualified_name(internal) for internal in target_deps.get("internals", [])]
                    requires += target_deps.get("externals", [])
                    system_libs = target_deps.get("system_libs", [])
                    frameworks = target_deps.get("frameworks", [])

                    component = self.cpp_info.components[conan_component_target_name]
                    component.set_property("cmake_target_name", target_lib)
                    component.libs = [target_lib]
                    component.requires = requires
                    component.system_libs = system_libs
                    component.frameworks = frameworks
                    if self.settings.os == "Windows" and not self.options.shared:
                        component.defines.append("OCCT_STATIC_BUILD")

                    component.requires.append(conan_component_target_name)

                    # TODO: to remove in conan v2 once cmake_find_package* generators removed
                    component.names["cmake_find_package"] = target_lib
                    component.names["cmake_find_package_multi"] = target_lib
                    component.build_modules["cmake_find_package"] = [self._cmake_module_file_rel_path]
                    component.build_modules["cmake_find_package_multi"] = [self._cmake_module_file_rel_path]

                # TODO: to remove in conan v2 once cmake_find_package* generators removed
                self.cpp_info.components[conan_component_module_name].names["cmake_find_package"] = module
                self.cpp_info.components[conan_component_module_name].names[
                    "cmake_find_package_multi"
                ] = module

        occt_modules_json_content = load(self._modules_helper_filepath)
        occt_modules = json.loads(occt_modules_json_content)
        _register_components(occt_modules)

        # DRAWEXE executable is not created if static build
        if self.options.shared:
            bin_path = os.path.join(self.package_folder, "bin")
            self.output.info(f"Appending PATH environment variable: {bin_path}")
            self.env_info.PATH.append(bin_path)

        # TODO: to remove in conan v2 once cmake_find_package* generators removed
        self.cpp_info.names["cmake_find_package"] = "OpenCASCADE"
        self.cpp_info.names["cmake_find_package_multi"] = "OpenCASCADE"
