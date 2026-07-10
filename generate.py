#!/usr/bin/env python3
"""Generate a CMake project from a TOML-backed template."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib


SUPPORTED_COMPILERS = {"msvc", "clang", "gcc", "clang-cl"}
DEFAULT_BUILD_TYPES = ["Debug", "RelWithDebInfo", "Release"]


@dataclass(frozen=True)
class ProjectModel:
    main_name: str
    sub_name: str
    sub_dir: str
    version: str
    description: str
    homepage_url: str
    languages: list[str]
    cxx_standard: int
    target_type: str
    qt_enabled: bool
    qt_sdk_dir: str
    qt_sdk_name: str
    qt_components: list[str]
    qt_qml_debug: bool
    preset_compilers: list[str]
    preset_build_types: list[str]
    preset_generator: str
    preset_arch: str
    preset_toolset: str
    preset_binary_dir: str
    preset_install_dir: str
    preset_generate_build: bool
    preset_generate_test: bool
    msvc_runtime: str
    use_sanitizers: bool
    vcpkg_root: str
    vcpkg_static_triplet: str
    vcpkg_dynamic_triplet: str
    include_third_party: bool
    link_what_you_use: bool
    win32_executable: bool
    macos_bundle: bool


def load_config(toml_path: str) -> dict[str, Any]:
    with open(toml_path, "rb") as f:
        return tomllib.load(f)


def as_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def as_list(value: Any, default: list[Any] | None = None) -> list[Any]:
    if value is None:
        return list(default or [])
    if isinstance(value, list):
        return value
    return [value]


def cmake_bool(value: bool) -> str:
    return "ON" if value else "OFF"


def compute_qt_sdk_name(sdk_dir: str) -> str:
    parts = sdk_dir.replace("\\", "/").strip("/").split("/")
    if len(parts) >= 2:
        return "_".join(parts[-2:])
    return parts[-1] if parts else ""


def normalize_build_type(build_type: str) -> str:
    lookup = {
        "debug": "Debug",
        "release": "Release",
        "relwithdebinfo": "RelWithDebInfo",
        "minsizerel": "MinSizeRel",
    }
    key = build_type.replace(" ", "").replace("_", "").replace("-", "").lower()
    if key not in lookup:
        raise ValueError(f"Unsupported build type: {build_type}")
    return lookup[key]


def normalize_compiler(compiler: str) -> str:
    normalized = compiler.strip().lower()
    aliases = {
        "clangcl": "clang-cl",
        "clang_cl": "clang-cl",
        "visualstudio": "msvc",
        "vs": "msvc",
    }
    normalized = aliases.get(normalized, normalized)
    if normalized not in SUPPORTED_COMPILERS:
        supported = ", ".join(sorted(SUPPORTED_COMPILERS))
        raise ValueError(f"Unsupported compiler '{compiler}'. Supported: {supported}")
    return normalized


def build_model(config: dict[str, Any]) -> ProjectModel:
    project = config.get("project", {})
    features = config.get("features", {})
    qt = config.get("qt", {})
    preset = config.get("presets", config.get("preset", {}))
    vcpkg = config.get("vcpkg", {})

    main_name = str(project.get("main_name", "main"))
    sub_name = str(project.get("sub_name", "") or main_name)
    sub_dir = str(project.get("sub_dir", "")) or ("src" if sub_name == main_name else sub_name)

    qt_sdk_dir = str(qt.get("sdk_dir", ""))
    qt_enabled = as_bool(qt.get("enabled"), bool(qt_sdk_dir))
    qt_sdk_name = str(qt.get("sdk_name", "")) or compute_qt_sdk_name(qt_sdk_dir)
    qt_components = [str(item) for item in as_list(qt.get("components"), ["Widgets"])]

    if qt_enabled:
        compiler_values = as_list(qt.get("compilers", qt.get("compiler")))
        if not compiler_values:
            compiler_values = [preset.get("default_compiler", "msvc")]
    else:
        compiler_values = as_list(preset.get("compilers"), ["msvc"])

    compilers = [normalize_compiler(str(item)) for item in compiler_values]
    build_types = [
        normalize_build_type(str(item))
        for item in as_list(preset.get("build_types"), DEFAULT_BUILD_TYPES)
    ]

    return ProjectModel(
        main_name=main_name,
        sub_name=sub_name,
        sub_dir=sub_dir,
        version=str(project.get("version", "1.0.0")),
        description=str(project.get("description", "")),
        homepage_url=str(project.get("homepage_url", "")),
        languages=[str(item) for item in as_list(project.get("languages"), ["CXX"])],
        cxx_standard=int(project.get("cxx_standard", 23)),
        target_type=str(project.get("target_type", "executable")).lower(),
        qt_enabled=qt_enabled,
        qt_sdk_dir=qt_sdk_dir,
        qt_sdk_name=qt_sdk_name,
        qt_components=qt_components,
        qt_qml_debug=as_bool(qt.get("qml_debug"), True),
        preset_compilers=list(dict.fromkeys(compilers)),
        preset_build_types=list(dict.fromkeys(build_types)),
        preset_generator=str(preset.get("generator", "Ninja")),
        preset_arch=str(preset.get("arch", "x64")),
        preset_toolset=str(preset.get("toolset", "v145")),
        preset_binary_dir=str(
            preset.get("binary_dir", "${sourceDir}/out/build/${presetName}")
        ),
        preset_install_dir=str(
            preset.get("install_dir", "${sourceDir}/out/install/${presetGroup}")
        ),
        preset_generate_build=as_bool(preset.get("generate_build_presets"), True),
        preset_generate_test=as_bool(preset.get("generate_test_presets"), False),
        msvc_runtime=str(preset.get("msvc_runtime", "MD")).upper(),
        use_sanitizers=as_bool(preset.get("use_sanitizers"), False),
        vcpkg_root=str(vcpkg.get("root", "")),
        vcpkg_static_triplet=str(vcpkg.get("static_triplet", "")),
        vcpkg_dynamic_triplet=str(vcpkg.get("dynamic_triplet", "")),
        include_third_party=as_bool(features.get("include_third_party"), False),
        link_what_you_use=as_bool(features.get("link_what_you_use"), True),
        win32_executable=as_bool(features.get("win32_executable"), True),
        macos_bundle=as_bool(features.get("macos_bundle"), True),
    )


def replace_in_file(file_path: Path, replacements: dict[str, str]) -> None:
    content = file_path.read_text(encoding="utf-8")
    for old, new in replacements.items():
        content = content.replace(old, new)
    file_path.write_text(content, encoding="utf-8")
    print(f"  Updated: {file_path}")


def make_replacements(model: ProjectModel) -> dict[str, str]:
    return {
        "#{MAIN_PROJECT_NAME}": model.main_name,
        "#{SUB_PROJECT_NAME}": model.sub_name,
        "#{SUB_PROJECT_DIR}": model.sub_dir,
        "#{PROJECT_VERSION}": model.version,
        "#{PROJECT_DESCRIPTION}": model.description,
        "#{PROJECT_HOMEPAGE_URL}": model.homepage_url,
        "#{PROJECT_LANGUAGES}": " ".join(model.languages),
        "#{CXX_STANDARD}": str(model.cxx_standard),
        "#{QT_SUPPORT_DEFAULT}": cmake_bool(model.qt_enabled),
        "#{QT_SDK_DIR}": model.qt_sdk_dir,
        "#{QT_SDK_NAME}": model.qt_sdk_name,
        "#{QT_COMPONENTS}": " ".join(model.qt_components),
        "#{TARGET_TYPE}": model.target_type,
        "#{LINK_WHAT_YOU_USE}": cmake_bool(model.link_what_you_use),
        "#{WIN32_EXECUTABLE}": cmake_bool(model.win32_executable),
        "#{MACOS_BUNDLE}": cmake_bool(model.macos_bundle),
        "#{GLOBAL_THIRD_PARTY_INCLUDE}": (
            "include(cmake/ThirdParty.cmake)" if model.include_third_party else ""
        ),
    }


def compiler_base_preset(compiler: str, model: ProjectModel) -> dict[str, Any]:
    preset: dict[str, Any] = {
        "name": f"{compiler}-base",
        "hidden": True,
        "inherits": "base",
        "displayName": f"Base Configuration for {compiler}",
        "description": f"Base preset for {compiler}",
        "cacheVariables": {},
    }

    cache = preset["cacheVariables"]
    uses_c = any(language.upper() == "C" for language in model.languages)
    if compiler == "msvc":
        if uses_c:
            cache["CMAKE_C_COMPILER"] = "cl.exe"
        cache.update({"CMAKE_CXX_COMPILER": "cl.exe", "MSVC_RUNTIME_MODE": model.msvc_runtime})
        preset["condition"] = {
            "type": "equals",
            "lhs": "${hostSystemName}",
            "rhs": "Windows",
        }
        preset["vendor"] = {
            "microsoft.com/VisualStudioSettings/CMake/1.0": {
                "intelliSenseMode": f"windows-msvc-{model.preset_arch}",
            }
        }
    elif compiler == "clang-cl":
        if uses_c:
            cache["CMAKE_C_COMPILER"] = "clang-cl.exe"
        cache.update(
            {"CMAKE_CXX_COMPILER": "clang-cl.exe", "MSVC_RUNTIME_MODE": model.msvc_runtime}
        )
        preset["condition"] = {
            "type": "equals",
            "lhs": "${hostSystemName}",
            "rhs": "Windows",
        }
    elif compiler == "clang":
        if uses_c:
            cache["CMAKE_C_COMPILER"] = "clang"
        cache["CMAKE_CXX_COMPILER"] = "clang++"
    elif compiler == "gcc":
        if uses_c:
            cache["CMAKE_C_COMPILER"] = "gcc"
        cache["CMAKE_CXX_COMPILER"] = "g++"

    return preset


def public_presets(model: ProjectModel) -> dict[str, Any]:
    configure_presets: list[dict[str, Any]] = [
        {
            "name": "base",
            "hidden": True,
            "displayName": "Base Configuration",
            "generator": model.preset_generator,
            "binaryDir": model.preset_binary_dir,
            "cacheVariables": {
                "CMAKE_EXPORT_COMPILE_COMMANDS": "ON",
                "CMAKE_CXX_STANDARD": str(model.cxx_standard),
                "CMAKE_CXX_STANDARD_REQUIRED": "ON",
                "CMAKE_CXX_EXTENSIONS": "OFF",
                "CMAKE_FIND_PACKAGE_PREFER_CONFIG": "ON",
                "USE_SANITIZERS": cmake_bool(model.use_sanitizers),
            },
        },
        {
            "name": "non-qt-base",
            "hidden": True,
            "inherits": "base",
            "cacheVariables": {"QT_SUPPORT": "OFF"},
        },
        {
            "name": "qt-base",
            "hidden": True,
            "inherits": "base",
            "cacheVariables": {
                "QT_SUPPORT": "ON",
                "CMAKE_PREFIX_PATH": "$env{QTDIR}",
            },
            "vendor": {
                "qt-project.org/Qt": {
                    "description": "Qt SDK is supplied by CMakeUserPresets.json"
                }
            },
        },
    ]
    configure_presets.extend(
        compiler_base_preset(compiler, model) for compiler in model.preset_compilers
    )

    return {
        "version": 9,
        "cmakeMinimumRequired": {"major": 3, "minor": 28, "patch": 0},
        "configurePresets": configure_presets,
    }


def preset_group_name(compiler: str, model: ProjectModel) -> str:
    if model.qt_enabled:
        return f"qt_{compiler}_{model.preset_arch}"
    return f"{compiler}_{model.preset_arch}"


def expand_preset_path(template: str, compiler: str, model: ProjectModel) -> str:
    return template.replace("${presetGroup}", preset_group_name(compiler, model))


def local_base_preset(compiler: str, model: ProjectModel) -> dict[str, Any]:
    mode_base = "qt-base" if model.qt_enabled else "non-qt-base"
    name = f"{'qt-' if model.qt_enabled else ''}{compiler}-{model.preset_arch}-local"
    preset: dict[str, Any] = {
        "name": name,
        "hidden": True,
        "inherits": [mode_base, f"{compiler}-base"],
        "architecture": {"value": model.preset_arch, "strategy": "external"},
        "installDir": expand_preset_path(model.preset_install_dir, compiler, model),
        "cacheVariables": {},
        "environment": {},
    }

    cache = preset["cacheVariables"]
    if compiler in {"msvc", "clang-cl"} and model.preset_toolset:
        preset["toolset"] = {"value": model.preset_toolset, "strategy": "external"}
    if model.vcpkg_root:
        cache["VCPKG_ROOT"] = model.vcpkg_root
    if model.vcpkg_static_triplet:
        cache["VCPKG_STATIC_TRIPLET"] = model.vcpkg_static_triplet
    if model.vcpkg_dynamic_triplet:
        cache["VCPKG_DYNAMIC_TRIPLET"] = model.vcpkg_dynamic_triplet
    if model.qt_enabled:
        if model.qt_sdk_dir:
            cache["QT_SDK_DIR"] = model.qt_sdk_dir
            preset["environment"]["QTDIR"] = model.qt_sdk_dir
        if model.qt_sdk_name:
            preset["displayName"] = f"Qt SDK {model.qt_sdk_name}"

    if not cache:
        del preset["cacheVariables"]
    if not preset["environment"]:
        del preset["environment"]
    return preset


def configure_preset_name(compiler: str, build_type: str, model: ProjectModel) -> str:
    suffix = build_type.lower()
    if model.qt_enabled:
        return f"qt_{compiler}_{model.preset_arch}_{suffix}"
    return f"{compiler}_{model.preset_arch}_{suffix}"


def user_presets(model: ProjectModel) -> dict[str, Any]:
    configure_presets: list[dict[str, Any]] = []
    build_presets: list[dict[str, Any]] = []
    test_presets: list[dict[str, Any]] = []

    for compiler in model.preset_compilers:
        local = local_base_preset(compiler, model)
        configure_presets.append(local)

        for build_type in model.preset_build_types:
            preset_name = configure_preset_name(compiler, build_type, model)
            display_prefix = "Qt " if model.qt_enabled else ""
            visible: dict[str, Any] = {
                "name": preset_name,
                "inherits": local["name"],
                "displayName": f"{display_prefix}{model.preset_arch} {build_type} {compiler}",
                "description": f"{build_type} build for {compiler}",
                "cacheVariables": {"CMAKE_BUILD_TYPE": build_type},
                "environment": {"BUILD_MODE": build_type.lower()},
            }

            if model.qt_enabled and model.qt_qml_debug and build_type == "Debug":
                visible["cacheVariables"]["CMAKE_CXX_FLAGS"] = "-DQT_QML_DEBUG"
                visible["environment"][
                    "QML_DEBUG_ARGS"
                ] = "-qmljsdebugger=file:${sourceDir}/.qt-qml-debug,block"

            configure_presets.append(visible)

            if model.preset_generate_build:
                build_presets.append(
                    {
                        "name": f"build-{preset_name}",
                        "configurePreset": preset_name,
                        "displayName": f"Build {preset_name}",
                    }
                )
            if model.preset_generate_test:
                test_presets.append(
                    {
                        "name": f"test-{preset_name}",
                        "configurePreset": preset_name,
                        "displayName": f"Test {preset_name}",
                        "output": {"outputOnFailure": True},
                    }
                )

    result: dict[str, Any] = {
        "version": 9,
        "configurePresets": configure_presets,
    }
    if build_presets:
        result["buildPresets"] = build_presets
    if test_presets:
        result["testPresets"] = test_presets
    if model.qt_enabled:
        result["vendor"] = {
            "qt-project.org/Presets": {
                "description": "Generated Qt user presets"
            }
        }
    return result


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"  Generated: {path}")


def cmake_args(options: dict[str, Any]) -> list[str]:
    args: list[str] = []
    if options.get("version"):
        args.append(str(options["version"]))
        if options.get("exact"):
            args.append("EXACT")
    for flag in [
        "required",
        "quiet",
        "config",
        "module",
        "no_module",
        "global",
        "allow_default_path",
    ]:
        if as_bool(options.get(flag)):
            args.append(flag.upper())
    for key, cmake_key in [
        ("components", "COMPONENTS"),
        ("optional_components", "OPTIONAL_COMPONENTS"),
        ("names", "NAMES"),
        ("hints", "HINTS"),
        ("paths", "PATHS"),
        ("path_suffixes", "PATH_SUFFIXES"),
    ]:
        values = [str(item) for item in as_list(options.get(key))]
        if values:
            args.append(cmake_key)
            args.extend(values)
    return args


def generate_dependencies(config: dict[str, Any], target_path: Path) -> None:
    deps = config.get("dependencies", {})
    if not deps:
        return

    lines = [
        "# Generated from project.toml. Keep project-specific dependency intent in TOML.",
        "",
    ]

    target_libraries = [str(item) for item in as_list(deps.get("target_libraries"))]

    for package in as_list(deps.get("vcpkg_packages")):
        if not isinstance(package, dict) or not package.get("name"):
            continue
        args = [str(package["name"])]
        if package.get("linkage"):
            args.extend(["LINKAGE", str(package["linkage"]).upper()])
        if package.get("triplet"):
            args.extend(["TRIPLET", str(package["triplet"])])
        args.extend(cmake_args(package))
        lines.append(f"FindVcpkgPackage({' '.join(args)})")
        target_libraries.extend(
            str(item) for item in as_list(package.get("target_libraries"))
        )

    for package in as_list(deps.get("find_packages")):
        if not isinstance(package, dict) or not package.get("name"):
            continue
        args = [str(package["name"])]
        args.extend(cmake_args(package))
        lines.append(f"find_package({' '.join(args)})")
        target_libraries.extend(
            str(item) for item in as_list(package.get("target_libraries"))
        )

    system_libraries = deps.get("system_libraries", {})
    if isinstance(system_libraries, dict):
        target_libraries.extend(str(item) for item in as_list(system_libraries.get("all")))
    if target_libraries:
        lines.extend(
            [
                "",
                "target_link_libraries(${PROJECT_NAME} PRIVATE",
                *[f"    {item}" for item in target_libraries],
                ")",
            ]
        )

    if isinstance(system_libraries, dict):
        for platform, cmake_condition in [
            ("windows", "WIN32"),
            ("linux", "UNIX AND NOT APPLE"),
            ("macos", "APPLE"),
        ]:
            libs = [str(item) for item in as_list(system_libraries.get(platform))]
            if libs:
                lines.extend(
                    [
                        "",
                        f"if({cmake_condition})",
                        "    target_link_libraries(${PROJECT_NAME} PRIVATE",
                        *[f"        {item}" for item in libs],
                        "    )",
                        "endif()",
                    ]
                )

    compile_definitions = [
        str(item) for item in as_list(deps.get("compile_definitions"))
    ]
    if compile_definitions:
        lines.extend(
            [
                "",
                "target_compile_definitions(${PROJECT_NAME} PRIVATE",
                *[f"    {item}" for item in compile_definitions],
                ")",
            ]
        )

    dlls = [str(item) for item in as_list(deps.get("copy_dynamic_libraries"))]
    if dlls:
        lines.extend(
            [
                "",
                "set(DYNAMIC_LINK_LIBRARY_LIST",
                *[f'    "{item}"' for item in dlls],
                ")",
                "CopyTargetDependentLibs(${PROJECT_NAME} \"${DYNAMIC_LINK_LIBRARY_LIST}\" ${VCPKG_DYNAMIC_BIN_PATH} ${VCPKG_DYNAMIC_DEBUG_BIN_PATH})",
            ]
        )

    target_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(f"  Generated: {target_path}")


def remove_output_dir(output_dir: Path, template_dir: Path) -> None:
    resolved_output = output_dir.resolve()
    resolved_template = template_dir.resolve()
    cwd = Path.cwd().resolve()

    if resolved_output in {cwd, resolved_template}:
        raise ValueError(f"Refusing to remove unsafe output directory: {output_dir}")
    if output_dir.exists():
        print(f"Removing existing output directory: {output_dir}")
        shutil.rmtree(output_dir)


def generate_project(args: argparse.Namespace) -> None:
    config = load_config(args.config)
    model = build_model(config)

    print("Configuration:")
    print(f"  MAIN_PROJECT    = {model.main_name}")
    print(f"  SUB_PROJECT     = {model.sub_name}")
    print(f"  SUB_PROJECT_DIR = {model.sub_dir}")
    print(f"  TARGET_TYPE     = {model.target_type}")
    print(f"  CXX_STANDARD    = {model.cxx_standard}")
    print(f"  QT_SUPPORT      = {cmake_bool(model.qt_enabled)}")
    if model.qt_enabled:
        print(f"  QT_SDK_DIR      = {model.qt_sdk_dir}")
        print(f"  QT_SDK_NAME     = {model.qt_sdk_name}")
    print(f"  PRESET_COMPILERS= {', '.join(model.preset_compilers)}")
    print(f"  BUILD_TYPES     = {', '.join(model.preset_build_types)}")

    template_dir = Path(args.template)
    if not template_dir.is_dir():
        raise FileNotFoundError(f"Template directory '{template_dir}' not found.")

    output_dir = Path(args.output) if args.output else Path(model.main_name)
    remove_output_dir(output_dir, template_dir)
    shutil.copytree(template_dir, output_dir)
    print(f"\nCopied template to: {output_dir}")

    replacements = make_replacements(model)
    for file_path in output_dir.rglob("*"):
        if file_path.is_file() and file_path.suffix.lower() in {".cmake", ".txt", ".json"}:
            replace_in_file(file_path, replacements)

    if model.sub_dir != "src":
        src_dir = output_dir / "src"
        dst_dir = output_dir / model.sub_dir
        if src_dir.is_dir() and not dst_dir.exists():
            src_dir.rename(dst_dir)
            print(f"  Renamed: src/ -> {model.sub_dir}/")

    write_json(output_dir / "CMakePresets.json", public_presets(model))
    write_json(output_dir / "CMakeUserPresets.json", user_presets(model))
    generate_dependencies(config, output_dir / model.sub_dir / "Dependencies.cmake")

    print("\nDone!")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate project from template")
    parser.add_argument("--config", default="project.toml", help="Path to TOML config")
    parser.add_argument("--template", default="template", help="Template directory")
    parser.add_argument(
        "--output", default=None, help="Output directory (default: <main_name>/)"
    )
    args = parser.parse_args()
    generate_project(args)


if __name__ == "__main__":
    main()
