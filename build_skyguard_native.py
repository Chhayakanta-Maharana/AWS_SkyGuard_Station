#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil

def main():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    dist_dir = os.path.join(project_dir, "dist")
    build_dir = os.path.join(project_dir, "build")
    spec_file = os.path.join(project_dir, "AWS_SkyGuard_Station.spec")

    print("==================================================")
    print("--- Packaging Standalone AWS SkyGuard Native App ---")
    print(f"Project Directory: {project_dir}")
    print(f"PyInstaller Spec:  {spec_file}")

    if os.name == 'nt':
        try:
            subprocess.run(["taskkill", "/f", "/im", "AWS_SkyGuard_Station.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    for path in [dist_dir, build_dir]:
        if os.path.exists(path):
            try:
                shutil.rmtree(path, ignore_errors=True)
            except Exception:
                pass

    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--noconfirm",
        spec_file
    ]

    print("\n>>> Running PyInstaller build command...")
    res = subprocess.run(pyinstaller_cmd, cwd=project_dir)
    if res.returncode != 0:
        print(f"Error: PyInstaller failed with code {res.returncode}")
        sys.exit(1)

    print("\n==================================================")
    print("BUILD COMPLETED SUCCESSFULLY!")
    print(f"Standalone native executable: {os.path.join(dist_dir, 'AWS_SkyGuard_Station.exe')}")
    print("==================================================")

if __name__ == "__main__":
    main()
