"""Hatchling build hook for the native (WPILib) dependencies and wheel polish.

During ``initialize`` the hook makes sure that the WPILib headers and static
libraries are available in the ``native/`` directory of the source tree.
``finalize`` then strips absolute RPATHs, regenerates the RECORD hashes, and
generates type stubs in the assembled wheel.  The C++ compilation itself is
done by Meson.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface

ROOT = Path(__file__).parent.resolve()


class NativeDepsBuildHook(BuildHookInterface):
    """Fetch the WPILib headers/libraries needed to compile YAMS."""

    PLUGIN_NAME = "custom"

    def initialize(self, version: str, build_data: dict) -> None:
        # semiwrap generates .pyi stubs by importing the freshly built module.
        # The stub generator currently rejects the raw WPILib/C++ type names
        # that appear in `py::doc` signatures, which aborts the build.  Skip the
        # automatic stub step; stubs can be generated separately once the
        # WPILib value types are wrapped.
        os.environ["SEMIWRAP_SKIP_PYI"] = "1"

        if version != "wheel":
            # The dependencies are fetched when a wheel is built.
            return

        prefix = ROOT / "native"
        include_dir = prefix / "include"
        lib_dir = prefix / "lib"

        if include_dir.is_dir() and lib_dir.is_dir() and any(lib_dir.glob("*.a")):
            return

        if os.environ.get("YAMS_SKIP_NATIVE_DEPS") == "1":
            raise RuntimeError(
                "the WPILib native dependencies are missing and "
                "YAMS_SKIP_NATIVE_DEPS=1 was set"
            )

        subprocess.run(
            [
                sys.executable,
                str(ROOT / "tools" / "fetch_native_deps.py"),
                "--prefix",
                str(prefix),
            ],
            check=True,
        )

    def finalize(self, version: str, build_data: dict, artifact_path: str) -> None:
        """Polish the wheel after it has been built.

        * strip absolute RPATHs from native extensions (Nix builds inject
          paths into the Nix store that do not exist on user machines), and
        * generate type stubs with ``pybind11-stubgen``.

        Semi-wrap's own stub step is disabled (``SEMIWRAP_SKIP_PYI``) because
        it rejects the raw WPILib/C++ type names that appear in some pybind11
        docstrings.  Re-running stubgen with a permissive
        ``--ignore-invalid-expressions`` pattern produces useful stubs.
        """
        if not artifact_path or not str(artifact_path).endswith(".whl"):
            return

        artifact = Path(artifact_path)
        with zipfile.ZipFile(artifact) as source:
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source.extractall(root)

                replacements: dict[str, bytes] = {}
                patchelf = None
                if sys.platform == "linux":
                    patchelf = shutil.which("patchelf")
                    if patchelf is None:
                        candidate = Path(sys.executable).with_name("patchelf")
                        if candidate.is_file():
                            patchelf = str(candidate)
                for extension in root.rglob("*.so"):
                    if patchelf is not None:
                        subprocess.run(
                            [patchelf, "--remove-rpath", str(extension)], check=True
                        )
                    # Always refresh the RECORD hash, even when patchelf is not
                    # available: the base wheel can contain a stale hash for the
                    # extension (for example after hatch-meson copies it in).
                    replacements[
                        extension.relative_to(root).as_posix()
                    ] = extension.read_bytes()

                stubs = self._generate_stubs(root)

                record_name = next(
                    (
                        info.filename
                        for info in source.infolist()
                        if info.filename.endswith(".dist-info/RECORD")
                    ),
                    None,
                )
                record = source.read(record_name).decode() if record_name else ""
                new_entries = dict(replacements)
                new_entries.update(stubs)
                if record_name and new_entries:
                    record = self._update_record(record, new_entries)

                patched = artifact.with_name(artifact.name + ".tmp")
                with zipfile.ZipFile(patched, "w") as target:
                    written: set[str] = set()
                    for info in source.infolist():
                        if info.filename == record_name:
                            data = record.encode()
                        else:
                            data = new_entries.get(info.filename)
                            if data is None:
                                data = source.read(info)
                        target.writestr(info, data)
                        written.add(info.filename)

                    for name, data in new_entries.items():
                        if name in written:
                            continue
                        info = zipfile.ZipInfo(name)
                        info.external_attr = 0o644 << 16
                        info.compress_type = zipfile.ZIP_DEFLATED
                        target.writestr(info, data)

        os.replace(patched, artifact)

    @staticmethod
    def _generate_stubs(root: Path) -> dict[str, bytes]:
        """Generate ``.pyi`` files for the wheel contents in ``root``."""
        output = root / "_stubs"
        environment = os.environ.copy()
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(root), environment.get("PYTHONPATH", "")]
        ).rstrip(os.pathsep)
        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pybind11_stubgen",
                    "--ignore-invalid-expressions=.*",
                    "--exit-code",
                    "-o",
                    str(output),
                    "yams",
                ],
                cwd=root,
                env=environment,
                check=True,
                capture_output=True,
                text=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            detail = getattr(exc, "stderr", "") or ""
            print(
                f"warning: unable to generate type stubs: {exc}\n{detail}",
                file=sys.stderr,
            )
            return {}

        return {
            path.relative_to(output).as_posix(): path.read_bytes()
            for path in output.rglob("*.pyi")
        }

    @staticmethod
    def _update_record(record: str, entries: dict[str, bytes]) -> str:
        """Update ``RECORD`` with the hashes of modified/added wheel entries."""
        import base64
        import csv
        import hashlib
        import io

        rows = list(csv.reader(io.StringIO(record)))
        index = {row[0]: position for position, row in enumerate(rows) if row}
        for name, data in entries.items():
            digest = base64.urlsafe_b64encode(hashlib.sha256(data).digest())
            digest = digest.rstrip(b"=").decode()
            row = [name, f"sha256={digest}", str(len(data))]
            if name in index:
                rows[index[name]] = row
            else:
                index[name] = len(rows)
                rows.append(row)

        output = io.StringIO()
        csv.writer(output, lineterminator="\n").writerows(rows)
        return output.getvalue()
