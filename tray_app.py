import ctypes
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

import pystray
from PIL import Image, ImageDraw
from dotenv import dotenv_values


PROJECT_DIR = Path(__file__).resolve().parent
APP_FILE = PROJECT_DIR / "app.py"
TRAY_FILE = PROJECT_DIR / "tray_app.py"
ENV_FILE = PROJECT_DIR / ".env"
ENV_EXAMPLE_FILE = PROJECT_DIR / ".env.example"
RUNTIME_DIR = PROJECT_DIR / "runtime"
SERVICE_PID_FILE = RUNTIME_DIR / "shutdown-api.pid"
TRAY_PID_FILE = RUNTIME_DIR / "shutdown-api-tray.pid"
LOG_FILE = PROJECT_DIR / "shutdown_service.log"
LAUNCHER_FILE = PROJECT_DIR / "启动休眠服务.bat"
STARTUP_LINK = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup" / "Shutdown API Tray.lnk"

PLACEHOLDER_SECRET = "change_me_session_secret"
PLACEHOLDER_PASSWORD = "change_me_login_password"
POLL_INTERVAL_SECONDS = 3
DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200
CREATE_NO_WINDOW = 0x08000000


def show_message(title: str, message: str) -> None:
    ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)


def ensure_runtime_dir() -> None:
    RUNTIME_DIR.mkdir(exist_ok=True)


def read_pid(pid_file: Path) -> int | None:
    try:
        value = pid_file.read_text(encoding="ascii").strip()
    except FileNotFoundError:
        return None
    except OSError:
        return None

    if not value.isdigit():
        return None
    return int(value)


def write_pid(pid_file: Path, pid: int) -> None:
    ensure_runtime_dir()
    pid_file.write_text(str(pid), encoding="ascii")


def remove_pid(pid_file: Path) -> None:
    try:
        pid_file.unlink()
    except FileNotFoundError:
        pass


def process_exists(pid: int | None) -> bool:
    if not pid:
        return False
    result = subprocess.run(
        ["tasklist", "/FI", f"PID eq {pid}"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    return str(pid) in result.stdout


def ensure_env_file() -> None:
    if not ENV_FILE.exists() and ENV_EXAMPLE_FILE.exists():
        shutil.copyfile(ENV_EXAMPLE_FILE, ENV_FILE)


def load_env_values() -> dict[str, str]:
    ensure_env_file()
    values = dotenv_values(ENV_FILE)
    return {str(k): str(v) for k, v in values.items() if k and v is not None}


def config_is_ready() -> bool:
    env = load_env_values()
    secret_key = env.get("SECRET_KEY", "").strip()
    username = env.get("APP_USERNAME", "").strip()
    password = env.get("APP_PASSWORD", "").strip()
    return bool(
        secret_key
        and secret_key != PLACEHOLDER_SECRET
        and username
        and password
        and password != PLACEHOLDER_PASSWORD
    )


def open_config() -> None:
    ensure_env_file()
    os.startfile(str(ENV_FILE))


def health_url() -> str:
    env = load_env_values()
    port = env.get("FLASK_PORT", "5000").strip() or "5000"
    return f"http://127.0.0.1:{port}/api/health"


def service_running() -> bool:
    pid = read_pid(SERVICE_PID_FILE)
    if not process_exists(pid):
        remove_pid(SERVICE_PID_FILE)
        return False
    return True


def service_healthy(timeout: float = 1.0) -> bool:
    if not service_running():
        return False
    try:
        with urllib.request.urlopen(health_url(), timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, ValueError):
        return False


def start_service() -> tuple[bool, str]:
    if service_running():
        return True, "服务已经在运行中。"

    if not config_is_ready():
        open_config()
        return False, "请先在 .env 里填写 SECRET_KEY、APP_USERNAME 和 APP_PASSWORD。"

    ensure_runtime_dir()
    creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    process = subprocess.Popen(
        [sys.executable, str(APP_FILE)],
        cwd=PROJECT_DIR,
        creationflags=creationflags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    write_pid(SERVICE_PID_FILE, process.pid)

    for _ in range(10):
        if service_healthy(timeout=0.5):
            return True, "服务已启动。"
        time.sleep(0.5)

    if process_exists(process.pid):
        return True, "服务已启动，但健康检查还没准备好。"

    remove_pid(SERVICE_PID_FILE)
    return False, "服务启动失败，请检查 .env 和 shutdown_service.log。"


def stop_service() -> tuple[bool, str]:
    pid = read_pid(SERVICE_PID_FILE)
    if not process_exists(pid):
        remove_pid(SERVICE_PID_FILE)
        return True, "服务已经是关闭状态。"

    result = subprocess.run(
        ["taskkill", "/PID", str(pid), "/F", "/T"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        creationflags=CREATE_NO_WINDOW,
        check=False,
    )
    remove_pid(SERVICE_PID_FILE)

    if result.returncode == 0:
        return True, "服务已停止。"
    return False, "关闭服务失败，请稍后重试。"


def restart_service() -> tuple[bool, str]:
    stop_success, stop_message = stop_service()
    if not stop_success:
        return False, stop_message

    time.sleep(1)
    return start_service()


def icon_image(color: str) -> Image.Image:
    image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.arc((8, 8, 56, 56), start=35, end=325, fill=color, width=8)
    draw.line((32, 14, 32, 32), fill=color, width=8)
    return image


def ps_quote(value: str) -> str:
    return value.replace("'", "''")


class TrayController:
    def __init__(self) -> None:
        self.icon = pystray.Icon(
            "shutdown-api-tray",
            icon_image("#eab308"),
            "自动休眠服务",
            menu=self.build_menu(),
        )
        self.status_text = "检查中"
        self.status_color = "#eab308"
        self.running = True

    def build_menu(self) -> pystray.Menu:
        return pystray.Menu(
            pystray.MenuItem(lambda _item: f"状态: {self.status_text}", lambda icon, item: None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("重启服务", self.on_restart_service),
            pystray.MenuItem("打开配置", self.on_open_config),
            pystray.MenuItem("打开日志", self.on_open_log),
            pystray.MenuItem("开机自启", self.on_toggle_autostart, checked=lambda item: self.autostart_enabled()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", self.on_exit_tray),
        )

    def autostart_enabled(self) -> bool:
        return STARTUP_LINK.exists()

    def set_autostart(self, enabled: bool) -> tuple[bool, str]:
        try:
            if enabled:
                startup_link = ps_quote(str(STARTUP_LINK))
                launcher_file = ps_quote(str(LAUNCHER_FILE))
                project_dir = ps_quote(str(PROJECT_DIR))
                icon_path = ps_quote(str(sys.executable))
                script = (
                    "$shell = New-Object -ComObject WScript.Shell;"
                    f"$shortcut = $shell.CreateShortcut('{startup_link}');"
                    f"$shortcut.TargetPath = '{launcher_file}';"
                    f"$shortcut.WorkingDirectory = '{project_dir}';"
                    f"$shortcut.IconLocation = '{icon_path},0';"
                    "$shortcut.Save();"
                )
                result = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="ignore",
                    creationflags=CREATE_NO_WINDOW,
                    check=False,
                )
                if result.returncode != 0:
                    return False, "修改开机自启失败。"
                return True, "已开启开机自启。"

            if STARTUP_LINK.exists():
                STARTUP_LINK.unlink()
            return True, "已关闭开机自启。"
        except Exception:
            return False, "修改开机自启失败。"

    def on_toggle_autostart(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        success, message = self.set_autostart(not self.autostart_enabled())
        self.refresh_state()
        if not success:
            show_message("自动休眠服务", message)

    def on_open_config(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        open_config()

    def on_open_log(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        if not LOG_FILE.exists():
            LOG_FILE.touch()
        os.startfile(str(LOG_FILE))

    def on_restart_service(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        success, message = restart_service()
        self.refresh_state()
        if not success:
            show_message("自动休眠服务", message)

    def on_exit_tray(self, icon: pystray.Icon, item: pystray.MenuItem) -> None:
        self.running = False
        stop_service()
        self.icon.stop()

    def refresh_state(self) -> None:
        if service_healthy():
            self.status_text = "运行中"
            self.status_color = "#16a34a"
        elif service_running():
            self.status_text = "启动中"
            self.status_color = "#eab308"
        elif config_is_ready():
            self.status_text = "未启动"
            self.status_color = "#dc2626"
        else:
            self.status_text = "等待配置"
            self.status_color = "#f97316"

        self.icon.icon = icon_image(self.status_color)
        self.icon.title = f"自动休眠服务 - {self.status_text}"
        self.icon.update_menu()

    def poll_loop(self) -> None:
        while self.running:
            self.refresh_state()
            time.sleep(POLL_INTERVAL_SECONDS)

    def run(self) -> None:
        self.refresh_state()
        threading.Thread(target=self.poll_loop, daemon=True).start()

        if config_is_ready():
            start_service()
        else:
            open_config()
            show_message("自动休眠服务", "请先在 .env 里填写 SECRET_KEY、APP_USERNAME 和 APP_PASSWORD。")

        self.icon.run()

def ensure_single_instance() -> bool:
    ensure_runtime_dir()
    existing_pid = read_pid(TRAY_PID_FILE)
    if process_exists(existing_pid):
        return False

    write_pid(TRAY_PID_FILE, os.getpid())
    return True


def cleanup() -> None:
    remove_pid(TRAY_PID_FILE)


def main() -> None:
    if not ensure_single_instance():
        return

    try:
        TrayController().run()
    finally:
        cleanup()


if __name__ == "__main__":
    main()
