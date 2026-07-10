cmake_minimum_required(VERSION 3.28)

project(#{MAIN_PROJECT_NAME}
    VERSION #{PROJECT_VERSION}
    DESCRIPTION "#{PROJECT_DESCRIPTION}"
    HOMEPAGE_URL "#{PROJECT_HOMEPAGE_URL}"
    LANGUAGES #{PROJECT_LANGUAGES}
)

set(CMAKE_CXX_STANDARD #{CXX_STANDARD})
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)
set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)

list(APPEND CMAKE_MODULE_PATH ${PROJECT_SOURCE_DIR}/cmake)
include(cmake/Global.cmake)
include(cmake/Functions.cmake)
# import global ThirdParty
#{GLOBAL_THIRD_PARTY_INCLUDE}
# Comes with third-party libraries and vcpkg management; whichever is added to the search path first will be found first.
include(cmake/VcpkgSetup.cmake) # vcpkg 3rdparty
include(cmake/CompilerConfigs.cmake)

set(PROJECT_BUILD_ARTIFACT_DIR "${CMAKE_BINARY_DIR}/artifacts/${CMAKE_BUILD_TYPE}/${PLATFORM_SUFFIX}")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/bin")
set(CMAKE_LIBRARY_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/lib")
set(CMAKE_ARCHIVE_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/lib")
set(CMAKE_PCH_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/pch")
set(CMAKE_ASM_LISTING_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/asm")
set(CMAKE_CXX_MODULE_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/modules")
if (COMPILER_MSVC)
  set(CMAKE_COMPILE_PDB_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/pdb")
  set(CMAKE_PDB_OUTPUT_DIRECTORY "${PROJECT_BUILD_ARTIFACT_DIR}/pdb")
endif()

option(QT_SUPPORT "Enable Qt framework support" #{QT_SUPPORT_DEFAULT})
if(QT_SUPPORT)
	set(CMAKE_AUTOUIC ON)
	set(CMAKE_AUTOMOC ON)
	set(CMAKE_AUTORCC ON)
	# generate.py replaces #{QT_SDK_DIR} when [qt] is configured in project.toml
	# For manual setup, set QT_SDK_DIR in CMake cache or via cmake -D
	if(NOT QT_SDK_DIR)
		set(QT_SDK_DIR "#{QT_SDK_DIR}" CACHE PATH "Path to Qt SDK (e.g. D:/Qt/6.6.2/msvc2019_64)")
	endif()
	message(STATUS "QT_SDK_DIR: ${QT_SDK_DIR}")
	list(APPEND CMAKE_PREFIX_PATH ${QT_SDK_DIR})

	find_package(QT NAMES Qt6 Qt5 REQUIRED COMPONENTS #{QT_COMPONENTS})
	find_package(Qt${QT_VERSION_MAJOR} REQUIRED COMPONENTS #{QT_COMPONENTS})

	if (${QT_VERSION} VERSION_LESS 6.1.0)
		set(BUNDLE_ID_OPTION MACOSX_BUNDLE_GUI_IDENTIFIER com.example.MAIN)
	endif()
endif()

add_subdirectory(#{SUB_PROJECT_DIR})
