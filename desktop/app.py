import os
import sys
import ctypes
import webbrowser
import subprocess
import time
import socket
import shutil
import traceback

# Explicit imports for PyInstaller backend packaging
try:
    import clr
    import clr_loader
except ImportError:
    pass

import webview
try:
    import webview.platforms.winforms
    import webview.platforms.edgechromium
    import webview.platforms.mshtml
except ImportError:
    pass

# Configure WebView2 and proxy settings before any other imports
os.environ["WEBVIEW2_ADDITIONAL_BROWSER_ARGUMENTS"] = "--no-proxy-server --disable-http-cache --disable-application-cache --disable-cache"
os.environ["no_proxy"] = "localhost,127.0.0.1"

def is_webview2_installed():
    import winreg
    keys = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"),
    ]
    for hive, path in keys:
        try:
            with winreg.OpenKey(hive, path, 0, winreg.KEY_READ) as key:
                val, _ = winreg.QueryValueEx(key, "pv")
                if val and val != "0.0.0.0":
                    return True
        except OSError:
            continue
    return False

def check_webview2_requirements():
    if os.name == 'nt':
        if not is_webview2_installed():
            msg = (
                "Microsoft Edge WebView2 Runtime is required to run the AWS SkyGuard Station dashboard, "
                "but it was not found on this system.\n\n"
                "Would you like to open the official download page to install it now?"
            )
            title = "WebView2 Runtime Required"
            res = ctypes.windll.user32.MessageBoxW(0, msg, title, 0x4 | 0x30 | 0x40000)
            if res == 6: # IDYES
                webbrowser.open("https://developer.microsoft.com/en-us/microsoft-edge/webview2/#download-section")
            sys.exit(1)

def setup_webview2_user_data_folder():
    local_appdata = os.environ.get("LOCALAPPDATA")
    if not local_appdata:
        return
    base_folder = os.path.join(local_appdata, "DRDO_AWS_SkyGuard_WebView2")
    os.makedirs(base_folder, exist_ok=True)
    os.environ["WEBVIEW2_USER_DATA_FOLDER"] = base_folder

check_webview2_requirements()
setup_webview2_user_data_folder()

# Determine if running in a bundle or from source
if getattr(sys, 'frozen', False):
    base_dir = sys._MEIPASS
    exe_dir = os.path.dirname(sys.executable)
    is_frozen = True
else:
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    exe_dir = base_dir
    is_frozen = False

def is_port_in_use(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def find_free_port(start_port=8080):
    port = start_port
    while is_port_in_use(port):
        port += 1
    return port

class DesktopApp:
    def __init__(self):
        self.backend_process = None
        self.port = find_free_port(8080)
        self.url = f"http://127.0.0.1:{self.port}"

    def start_backend(self):
        # Kill any old telemetry backend to ensure file locks are clean
        if os.name == 'nt':
            try:
                subprocess.run(["taskkill", "/f", "/im", "aws-telemetry-backend.exe"], 
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        backend_name = "aws-telemetry-backend.exe"
        if is_frozen:
            backend_exe = os.path.join(base_dir, "backend", backend_name)
            static_dir = os.path.join(base_dir, "frontend", "out")
        else:
            backend_exe = os.path.join(base_dir, "backend", backend_name)
            static_dir = os.path.join(base_dir, "frontend", "out")

        # Fallback to dev binary name if exists
        if not os.path.exists(backend_exe) and not is_frozen:
            alternative_exe = os.path.join(base_dir, "backend", "main.exe")
            if os.path.exists(alternative_exe):
                backend_exe = alternative_exe

        print(f"Starting Go backend from {backend_exe}...")
        print(f"Serving static frontend files from: {static_dir}")

        cmd = [
            backend_exe,
            "-port", str(self.port),
            "-static-dir", static_dir
        ]

        startupinfo = None
        if os.name == 'nt':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE

        log_dir = os.path.join(exe_dir, "logs")
        os.makedirs(log_dir, exist_ok=True)
        
        self.stdout_file = open(os.path.join(log_dir, "backend_stdout.log"), "a", encoding="utf-8")
        self.stderr_file = open(os.path.join(log_dir, "backend_stderr.log"), "a", encoding="utf-8")

        try:
            self.backend_process = subprocess.Popen(
                cmd,
                cwd=exe_dir,
                startupinfo=startupinfo,
                stdout=self.stdout_file,
                stderr=self.stderr_file,
                text=True
            )
        except Exception as e:
            err_msg = f"Failed to spawn Go backend:\n{e}"
            if os.name == 'nt':
                ctypes.windll.user32.MessageBoxW(0, err_msg, "Backend Spawn Failure", 0x10)
            sys.exit(1)

        # Wait for Go backend to respond
        time.sleep(2)

    def stop_backend(self):
        if self.backend_process:
            self.backend_process.terminate()
            try:
                self.backend_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.backend_process.kill()
            
            try:
                self.stdout_file.close()
                self.stderr_file.close()
            except Exception:
                pass

def main():
    try:
        app = DesktopApp()
        app.start_backend()

        window = webview.create_window(
            "AUTOMATED WEATHER STATION - SkyGuard Ground Telemetry Station",
            url=app.url,
            width=1920,
            height=1080,
            min_size=(1200, 780),
            background_color="#060913",
            text_select=False,
            zoomable=True
        )

        def on_closed():
            app.stop_backend()

        window.events.closed += on_closed
        try:
            webview.start(gui="edgechromium", debug=False)
        except Exception:
            webview.start(debug=False)
    except Exception as e:
        crash_log = os.path.join(exe_dir, "app_crash.log")
        err_msg = f"Fatal Error Starting Desktop Console:\n\n{traceback.format_exc()}"
        try:
            with open(crash_log, "w", encoding="utf-8") as f:
                f.write(err_msg)
        except Exception:
            pass
        if os.name == 'nt':
            ctypes.windll.user32.MessageBoxW(0, err_msg, "SkyGuard Station Error", 0x10)
        sys.exit(1)

if __name__ == "__main__":
    main()
