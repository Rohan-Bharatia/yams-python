#!/usr/bin/env python3
"""Download and unpack the native WPILib dependencies used to build YAMS.

YAMS is a header + source library that builds against WPILib's C++ API.  The
upstream project expects a full WPILib installation (vendored through
``frcmaven``); this script reproduces just the pieces that are needed to
compile the YAMS C++ sources into a Python extension module:

* the WPILib C++ headers, and
* the WPILib static libraries (linked statically into the extension module so
  that the resulting wheel is self contained and needs no ``RPATH`` tricks).

The artifacts are downloaded from the WPILib maven repository, verified against
a pinned SHA-256 digest and unpacked into a prefix directory (``native/`` by
default).

Usage::

    python tools/fetch_native_deps.py [--prefix native] [--force]
"""

from __future__ import annotations

import argparse
import hashlib
import os
import platform
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

#: The WPILib release that YAMS is built against.
WPILIB_VERSION = "2027.0.0-alpha-7"

#: Base URL of the WPILib maven repository.
MAVEN_BASE = "https://frcmaven.wpi.edu/artifactory/release/org/wpilib"

#: The WPILib artifacts that YAMS depends on.
ARTIFACTS = (
    "wpiutil",
    "wpimath",
    "wpinet",
    "ntcore",
    "datalog",
    "hal",
    "wpilibc",
    "commandsv2",
    "telemetry",
    "tunables",
)

#: Maps ``(sys.platform, machine)`` onto the artifact platform tag.
PLATFORM_TAGS = {
    ("linux", "x86_64"): "linuxx86-64",
    ("linux", "aarch64"): "linuxarm64",
    ("linux", "arm64"): "linuxarm64",
    ("darwin", "x86_64"): "osxuniversal",
    ("darwin", "arm64"): "osxuniversal",
    ("win32", "x86_64"): "windowsx86-64",
    ("win32", "amd64"): "windowsx86-64",
    ("win32", "ARM64"): "windowsarm64",
    ("cygwin", "x86_64"): "windowsx86-64",
    ("msys", "x86_64"): "windowsx86-64",
}

#: Pinned SHA-256 digests of the downloaded archives.  Keyed by
#: ``(artifact, kind, platform tag)``.
CHECKSUMS = {
    ("wpiutil", "headers"): "d2a90dc91b34f15af97921e058ab52540dd0876400969650ae33783ff314f7b7",
    ("wpimath", "headers"): "3d7ff6a561655238e6b5ff9d0ab26c202922f6e7f4ea3189d23e67dfea8a6dc6",
    ("wpinet", "headers"): "f2eff5f6e2e2e0aa6a175aeed7e4a7e3e914e895b159f3c1291c08ad3d63aaf2",
    ("ntcore", "headers"): "d5f869563a5b8e8ba396923ad5f6878a3bd83fef27fa201b49fe7efdc5d92114",
    ("datalog", "headers"): "1854eb2ce6e371247b077205f043a7443d32b53b34c1f51a77a51b821e867933",
    ("hal", "headers"): "63c1d6332962ef8d922787707513f4f47cee5fe3b30dd90cb5d741237c7f7d11",
    ("wpilibc", "headers"): "53a3a6601cdf74b8e57096f822f2649174691a255a7892556d6b3a1ef37444ab",
    ("commandsv2", "headers"): "d9c2a7bc439a7226c3f0815ce519e07c4902b1c6c9210de2b747e9d97c9d0a9a",
    ("telemetry", "headers"): "f846fea8cd9c1ed2ace6b6505dcfc6b9268f072dab68f53f6f0d564f0321fd9d",
    ("tunables", "headers"): "ec4b9af4b17da7797dbc083fd810b8b54d962b2af0f40e7aa5fdc73b6687da1a",
    ("wpiutil", "linuxx86-64"): "7dd84aa6c50707429feeda116b1a019e0198192e0c63e0941547172c2eaab186",
    ("wpimath", "linuxx86-64"): "bd2d0b0ff1bcec3a922b3a16acf1b9842550af15f523d7d55b32f7a484d2a8f9",
    ("wpinet", "linuxx86-64"): "db7e4fb37ea353921eee8be3e444c18c0eca35482575f28aed753e27e5ba526e",
    ("ntcore", "linuxx86-64"): "09a1f9fd41937cea3e7e6e2bdffb29b504d02fdb5703646ef9750e953081fff9",
    ("datalog", "linuxx86-64"): "b561d7ab849eed96dc64ae812515a8ee5829a8b32017d9b0e576ae999c042b6a",
    ("hal", "linuxx86-64"): "bc55c1bbc95bfb1eabae2a962b293de37d2a1cb2ac795fd9d139c85504f6ba56",
    ("wpilibc", "linuxx86-64"): "46e9b5b362e3e7cd25c01b50ddab4e22e17b8799eb330ea0c5842a6d4a4cef3b",
    ("commandsv2", "linuxx86-64"): "e23cbfed459c6728e34037736eb971b3989baa1df75dc8ecd0bad849b44083c3",
    ("telemetry", "linuxx86-64"): "ffcd4abaf7ab49aa35bdd5bcd57538db373711d4a93a6ee3f4e536aee01b9161",
    ("tunables", "linuxx86-64"): "07ad3a2d7682c1e6fe42db7630ddf88a07ee23811736bfdf07e852411ae0da46",
    ("wpiutil", "linuxarm64"): "420163eeb641adbff8848be323fd9305f556eef6f873e51fd5117b773ebc31ed",
    ("wpimath", "linuxarm64"): "c35de8711dddeefd127b43927d8cca5e8ab5ab34dbb0ec6d438789f80d8dcaae",
    ("wpinet", "linuxarm64"): "ac5ea66c50a042672174784bc737121023c1a441449d88d69b70c2f9d397692b",
    ("ntcore", "linuxarm64"): "b36cd53b2d608d54b1b4e307e908d32a72f26e21eac019cbbc7fdb97577b9fa3",
    ("datalog", "linuxarm64"): "a58f63ede2339d3c6fd57a3b53b9df92982ca2d59a66134d48d36c4b344793f5",
    ("hal", "linuxarm64"): "19899b95144d14f63124423764e28eee46a9991403a7602e88ae63d6456464fe",
    ("wpilibc", "linuxarm64"): "30aa9bd4992f7e25dbac7bae8c0f4fe6368ab4bf69cba26d35b9a002d1411355",
    ("commandsv2", "linuxarm64"): "28ae9349081d8ef824fe6c257d7180b694b1cd8ae78bc5d7e531b2a8f743e761",
    ("telemetry", "linuxarm64"): "93c21dd8b9824b57fd9055e2af3fb8059d65ddab031489fd10afa97e88be7679",
    ("tunables", "linuxarm64"): "3f88a45593ae36e5ff9ab1ec23813793bc848888a07a92513cac301df6919003",
    ("wpiutil", "osxuniversal"): "3e429ef934d7a1d241ef7efcded41c1caee14d06def4d20c58d9085d53282ebd",
    ("wpimath", "osxuniversal"): "db27ae365a7e1b25de26984d01613cf7b2b3386a9b2f87b67cda63724197f2e9",
    ("wpinet", "osxuniversal"): "5e68d095b4daa9d063373ac4df902f45042d4c855c1dc692b4ee98344c436fd9",
    ("ntcore", "osxuniversal"): "cca26646f661f8462ee77a51e19ef84ac2087adc387c515732270206757d6736",
    ("datalog", "osxuniversal"): "3bfb12431cbd7d870840ce4c59c4194de9490d894274346db196364ac9976948",
    ("hal", "osxuniversal"): "06f092316c3cdc370f28f4dcda34364b41a93d5076df36bf72299db8f429925e",
    ("wpilibc", "osxuniversal"): "7e0e731f8292cb7188118bea0249b1bdea206166b54eb8e7d2bf89257dda322b",
    ("commandsv2", "osxuniversal"): "c0ab121f23d50d7401b967235ebc41256c094cf318f124ab18da90bf5426d343",
    ("telemetry", "osxuniversal"): "ba6a72dc541173ed3b79df5a2a0e61a392b9d7261e3181ad50b6ba1e247c90eb",
    ("tunables", "osxuniversal"): "a0351aad15ec9277df070697f51a2d97effbe6eb1107b2450f35df4b14654d69",
    ("wpiutil", "windowsx86-64"): "1893455a4aa4e0f34d104602fa4a366aeb2b1824698a8e41bcfdbb7717af05a7",
    ("wpimath", "windowsx86-64"): "60586eff8d72ffdbc895328e1fc3b3fd68377d1c695aa640aa09f2f37be8c146",
    ("wpinet", "windowsx86-64"): "4684d4e5e65de6937bb8504da7e810b58af02d3b1b4ee64e9fe9357b1a21239d",
    ("ntcore", "windowsx86-64"): "0dc778ab01c573602bb26a4797686e26a0ce962bbe0a5f6bbb946d88b628904c",
    ("datalog", "windowsx86-64"): "056c73a8a5a4ef512e77cf60e21725abc614f48d49cf2312a5d8516451c9acc6",
    ("hal", "windowsx86-64"): "37fd6668ba2171b8a5c7d4a66b95103a7c8684e52ae0585dd19368fefd1f8a4a",
    ("wpilibc", "windowsx86-64"): "98476205866e1e6fdfb8dbc937ffeca6531bb2a0c264c343e515054304e3be06",
    ("commandsv2", "windowsx86-64"): "fee195506fa3e06e78359669b7637365fd7ee7db1914a5798173da5c772b20ff",
    ("telemetry", "windowsx86-64"): "161c8e9d2a376df48570edac3f286522a918901585bf8f6e679d1acfbdd23ea0",
    ("tunables", "windowsx86-64"): "4c0b8dd98706a6f94210405a13bee5ca22f25f8c2807841e8dbba48a60a722c6",
}


def platform_tag() -> str:
    """Return the WPILib artifact tag for the current interpreter."""
    key = (sys.platform, platform.machine())
    try:
        return PLATFORM_TAGS[key]
    except KeyError:
        raise SystemExit(
            f"unsupported platform {key!r}; set YAMS_WPILIB_PLATFORM to one of "
            f"{sorted(set(PLATFORM_TAGS.values()))}"
        ) from None


def artifact_url(artifact: str, kind: str, tag: str) -> str:
    """Return the download URL of a single artifact."""
    suffix = "headers" if kind == "headers" else f"{tag}static"
    name = f"{artifact}-cpp-{WPILIB_VERSION}-{suffix}.zip"
    return f"{MAVEN_BASE}/{artifact}/{artifact}-cpp/{WPILIB_VERSION}/{name}"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, dest: Path, expect: str | None) -> None:
    """Download ``url`` to ``dest``, verifying its SHA-256 digest."""
    if dest.exists() and expect and sha256(dest) == expect:
        return
    print(f"  downloading {url}", file=sys.stderr)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(url, timeout=120) as response, tmp.open("wb") as fp:
            shutil.copyfileobj(response, fp)
    except urllib.error.URLError as exc:  # pragma: no cover - network failure
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"failed to download {url}: {exc}") from exc
    if expect:
        actual = sha256(tmp)
        if actual != expect:
            tmp.unlink(missing_ok=True)
            raise SystemExit(
                f"checksum mismatch for {url}\n  expected {expect}\n  got      {actual}"
            )
    tmp.replace(dest)


def extract(archive: Path, dest: Path, licenses: Path) -> None:
    """Extract ``archive`` into ``dest``.

    The upstream archives contain the headers (respectively the libraries)
    below a platform specific directory, and the WPILib license files.  The
    libraries are flattened into ``dest`` and the license files are collected
    in ``licenses``.
    """
    dest.mkdir(parents=True, exist_ok=True)
    licenses.mkdir(parents=True, exist_ok=True)
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(dest)
            for name in zf.namelist():
                if name.endswith(("LICENSE.md", "ThirdPartyNotices.txt")):
                    target = licenses / f"{archive.name[:-4]}-{Path(name).name}"
                    shutil.copyfile(dest / name, target)
    elif archive.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(archive) as tf:
            tf.extractall(dest)
    else:  # pragma: no cover - defensive
        raise SystemExit(f"unsupported archive format: {archive}")

    for lib in dest.rglob("*.a"):
        if lib.parent != dest:
            shutil.move(str(lib), str(dest / lib.name))


def strip_archives(libdir: Path) -> None:
    """Remove debug information from the static archives.

    The upstream archives are built with debug information, which makes them
    roughly 40x larger.  The debug information is not needed to link against
    them, so it is stripped in place.
    """
    objcopy = shutil.which("objcopy")
    if objcopy is None:
        print("  objcopy not found, keeping archives as-is", file=sys.stderr)
        return
    for archive in sorted(libdir.glob("*.a")):
        subprocess.run(
            [objcopy, "--strip-debug", str(archive)],
            check=True,
            stdout=subprocess.DEVNULL,
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--prefix",
        type=Path,
        default=Path("native"),
        help="directory the headers and libraries are unpacked into",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-download and re-extract everything",
    )
    args = parser.parse_args(argv)

    tag = os.environ.get("YAMS_WPILIB_PLATFORM") or platform_tag()
    prefix = args.prefix.resolve()
    include_dir = prefix / "include"
    lib_dir = prefix / "lib"
    license_dir = prefix / "licenses"
    cache_dir = prefix / "cache"

    if args.force:
        shutil.rmtree(prefix, ignore_errors=True)

    include_dir.mkdir(parents=True, exist_ok=True)
    lib_dir.mkdir(parents=True, exist_ok=True)
    license_dir.mkdir(parents=True, exist_ok=True)
    cache_dir.mkdir(parents=True, exist_ok=True)

    for artifact in ARTIFACTS:
        for kind in ("headers", "lib"):
            if kind == "headers":
                url = artifact_url(artifact, "headers", tag)
                expect = CHECKSUMS.get((artifact, "headers"))
                name = url.rsplit("/", 1)[-1]
            else:
                url = artifact_url(artifact, "lib", tag)
                expect = CHECKSUMS.get((artifact, tag))
                name = url.rsplit("/", 1)[-1]

            if expect is None:
                if kind == "headers":
                    pinned = sorted(
                        {key[0] for key in CHECKSUMS if key[1] == "headers"}
                    )
                    detail = (
                        f"none of the pinned header checksums cover {artifact!r}; "
                        f"pinned artifacts: {pinned}"
                    )
                else:
                    pinned = sorted(
                        {key[1] for key in CHECKSUMS if key[1] != "headers"}
                    )
                    detail = (
                        f"the {tag!r} libraries are not pinned; pinned platforms: "
                        f"{pinned}\n"
                        f"Set YAMS_WPILIB_PLATFORM to a pinned tag, or add and "
                        f"verify checksums for {tag!r}"
                    )
                raise SystemExit(
                    f"no pinned SHA-256 checksum for {artifact} ({kind}).\n"
                    f"Refusing to download unverified archives: {detail}.\n"
                    f"Add the checksums to CHECKSUMS in {Path(__file__).name} "
                    f"after verifying the downloads manually."
                )

            archive = cache_dir / name
            download(url, archive, expect)

            if kind == "headers":
                extract(archive, include_dir, license_dir)
            else:
                extract(archive, lib_dir, license_dir)

    strip_archives(lib_dir)

    print(f"WPILib {WPILIB_VERSION} ({tag}) installed in {prefix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


# Additional aliases for Python wheels and cross-platform names
PLATFORM_TAGS.update({
    ("linux", "aarch64_be"): "linuxarm64",
})
