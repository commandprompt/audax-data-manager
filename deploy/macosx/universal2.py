"""Makes the packages in the active virtual environment universal2 (x86_64 + arm64).

PyInstaller can build an arm64 app on an Intel Mac only if the interpreter and every
native extension contain an arm64 slice. Packages that PyPI ships as separate x86_64 and
arm64 wheels (or only as source) are replaced with fused universal2 builds.
"""
import subprocess
import sys
import tempfile
from importlib.metadata import distributions
from pathlib import Path

# source-only on PyPI, the binary distribution provides the same module
BINARY_DIST = {"psycopg2": "psycopg2-binary"}

X64_PLATFORMS = [f"macosx_{v}_x86_64" for v in ("14_0", "13_0", "12_0", "11_0", "10_15", "10_9")]
ARM64_PLATFORMS = [f"macosx_{v}_arm64" for v in ("14_0", "13_0", "12_0", "11_0")]


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True).stdout


def lacks_arm64(path):
    return "arm64" not in run("lipo", "-archs", str(path)).split()


def thin_dists():
    found = {}
    for dist in distributions():
        name = dist.metadata["Name"]
        if name.lower() == "delocate":  # build tool, its test data is not part of the app
            continue
        if name.lower() in BINARY_DIST:  # compiled against the host libpq, which has no arm64 slice
            found[name] = dist.version
            continue
        for f in dist.files or []:
            if f.suffix in (".so", ".dylib") and lacks_arm64(f.locate()):
                found[name] = dist.version
    return found


def download(name, version, platforms, dest):
    args = [sys.executable, "-m", "pip", "download", "--no-deps", "--only-binary=:all:",
            "--python-version", "3.11", "--implementation", "cp",
            "--abi", "cp311", "--abi", "abi3", "--abi", "none", "-d", str(dest), f"{name}=={version}"]
    for platform in platforms:
        args += ["--platform", platform]
    run(*args)
    return next(Path(dest).glob("*.whl"))


def main():
    thin = thin_dists()
    if not thin:
        print("all native extensions are already universal2")
        return

    with tempfile.TemporaryDirectory() as tmp:
        fused = []
        for name, version in thin.items():
            name = BINARY_DIST.get(name.lower(), name)
            print(f"fusing {name}=={version}")
            x64 = download(name, version, X64_PLATFORMS, Path(tmp) / name / "x64")
            arm64 = download(name, version, ARM64_PLATFORMS, Path(tmp) / name / "arm64")
            out = Path(tmp) / name / "fused"
            run("delocate-merge", str(x64), str(arm64), "-w", str(out))
            fused.append(next(out.glob("*.whl")))

        for name in thin:
            if name.lower() in BINARY_DIST:
                run(sys.executable, "-m", "pip", "uninstall", "-y", name)
        run(sys.executable, "-m", "pip", "install", "--force-reinstall", "--no-deps", *map(str, fused))

    still_thin = thin_dists()
    if still_thin:
        sys.exit(f"packages without an arm64 slice: {', '.join(still_thin)}")


main()
