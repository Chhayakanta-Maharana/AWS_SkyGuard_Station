import os
import sys
import subprocess
import shutil

# Define paths relative to this script
desktop_dir = os.path.dirname(os.path.abspath(__file__))
project_dir = os.path.dirname(desktop_dir)
frontend_dir = os.path.join(project_dir, "frontend")
backend_dir = os.path.join(project_dir, "backend")

def run_command(cmd, cwd, description):
    print(f"\n>>> Running: {description}...")
    print(f"Command: {' '.join(cmd)} in {cwd}")
    
    is_win = sys.platform == "win32"
    result = subprocess.run(cmd, cwd=cwd, shell=is_win, text=True)
    if result.returncode != 0:
        print(f"Error: {description} failed with exit code {result.returncode}")
        sys.exit(1)
    print(f"Success: {description} completed.")

def main():
    print("==================================================")
    print("--- 1. Building Frontend (Next.js Static Export) ---")
    out_dir = os.path.join(frontend_dir, "out")
    if not (os.path.exists(out_dir) and os.path.exists(os.path.join(out_dir, "index.html"))):
        if not os.path.exists(os.path.join(frontend_dir, "node_modules")):
            run_command(["npm", "install"], frontend_dir, "Installing npm packages")
        run_command(["npm", "run", "build"], frontend_dir, "Building static frontend export")
    else:
        print(f"Frontend static export already built at: {out_dir}")
    
    if not os.path.exists(out_dir) or not os.path.exists(os.path.join(out_dir, "index.html")):
        print(f"Error: Next.js static build did not output index.html to {out_dir}")
        sys.exit(1)
    print(f"Frontend static files successfully exported to {out_dir}")

    print("\n--- 2. Compiling Go Backend ---")
    backend_exe = os.path.join(backend_dir, "aws-telemetry-backend.exe")
    run_command(["go", "build", "-o", "aws-telemetry-backend.exe", "."], backend_dir, "Compiling Go backend executable")
    
    if not os.path.exists(backend_exe):
        print(f"Error: Go backend compilation did not produce {backend_exe}")
        sys.exit(1)
    print(f"Go backend compiled successfully: {backend_exe}")

    print("\n--- 3. Checking Python Dependencies ---")
    use_uv = shutil.which("uv") is not None
    install_tool = ["uv", "pip", "install", "--system"] if use_uv else [sys.executable, "-m", "pip", "install"]
    run_command(install_tool + ["pywebview", "pyinstaller"], project_dir, "Installing pywebview and pyinstaller")

    print("\n--- 4. Packaging Standalone Executable using PyInstaller ---")
    dist_dir = os.path.join(project_dir, "dist")
    build_dir = os.path.join(project_dir, "build")
    spec_file = os.path.join(project_dir, "AWS_SkyGuard_Station.spec")

    # Kill any open running instance so PyInstaller can write cleanly
    if sys.platform == "win32":
        try:
            subprocess.run(["taskkill", "/f", "/im", "AWS_SkyGuard_Station.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["taskkill", "/f", "/im", "aws-telemetry-backend.exe"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
    
    for path in [dist_dir, build_dir, spec_file]:
        if os.path.exists(path):
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    os.remove(path)
            except Exception:
                pass
                
    pyinstaller_cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--clean",
        "--onefile",
        "--noconsole",
        "--name", "AWS_SkyGuard_Station",
        "--add-data", f"{os.path.join(backend_dir, 'aws-telemetry-backend.exe')}{os.pathsep}backend",
        "--add-data", f"{os.path.join(frontend_dir, 'out')}{os.pathsep}frontend/out",
        os.path.join(desktop_dir, "app.py")
    ]
    
    run_command(pyinstaller_cmd, project_dir, "Packaging with PyInstaller")
    
    final_exe = os.path.join(dist_dir, "AWS_SkyGuard_Station.exe")
    if os.path.exists(final_exe):
        print("\n==================================================")
        print("BUILD COMPLETED SUCCESSFULLY!")
        print(f"Standalone executable is available at: {final_exe}")
        print("==================================================")
    else:
        print(f"Error: Final executable not found at {final_exe}")
        sys.exit(1)

if __name__ == "__main__":
    main()
