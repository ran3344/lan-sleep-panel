"""
Windows remote shutdown web service.
"""

import logging
import subprocess
from datetime import datetime, timedelta
from functools import wraps
from logging.handlers import TimedRotatingFileHandler

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from waitress import serve

from config import Config


app = Flask(__name__)
app.secret_key = Config.SECRET_KEY
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=7)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        TimedRotatingFileHandler(
            "shutdown_service.log",
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
    ],
)
logger = logging.getLogger(__name__)
logging.getLogger("werkzeug").disabled = True


def client_ip() -> str:
    return request.remote_addr or ""


def is_logged_in() -> bool:
    return session.get("logged_in") is True


def parse_delay(value) -> int:
    try:
        delay = int(value)
    except (TypeError, ValueError):
        return 0
    return max(delay, 0)


def resolve_shutdown_delay(form_data) -> tuple[int, str]:
    preset_value = form_data.get("delay_preset", form_data.get("delay", 0))
    delay = parse_delay(preset_value)

    labels = {
        0: "将立即执行关机。",
        300: "将在 5 分钟后执行关机。",
        1800: "将在 30 分钟后执行关机。",
        3600: "将在 1 小时后执行关机。",
        10800: "将在 3 小时后执行关机。",
        18000: "将在 5 小时后执行关机。",
    }
    return delay, labels.get(delay, f"将在 {delay} 秒后执行关机。")


def parse_force(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def log_prefix() -> str:
    return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]"


def ip_whitelist_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        ip = client_ip()
        if not Config.is_ip_allowed(ip):
            logger.warning(f"IP whitelist denied: {ip}")
            if request.path.startswith("/api/"):
                return jsonify({"code": 403, "message": "Access denied."}), 403
            return "Access denied.", 403
        return view_func(*args, **kwargs)

    return wrapped


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not is_logged_in():
            if request.path.startswith("/api/"):
                return jsonify({"code": 401, "message": "Login required."}), 401
            return redirect(url_for("login", next=request.path))
        return view_func(*args, **kwargs)

    return wrapped


def execute_shutdown(delay: int = 0, force: bool = False) -> tuple[bool, str]:
    try:
        cmd = ["shutdown", "-s", "-t", str(delay)]
        if force:
            cmd.append("-f")

        logger.info(f"Execute shutdown command: {' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            return True, "Shutdown command executed successfully."

        error_msg = result.stderr.strip() or "Unknown error"
        logger.error(f"Shutdown command failed: {error_msg}")
        return False, error_msg
    except subprocess.TimeoutExpired:
        logger.error("Shutdown command timeout")
        return False, "Command execution timeout."
    except Exception as exc:
        logger.error(f"Shutdown command exception: {exc}")
        return False, str(exc)


def execute_cancel_shutdown() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["shutdown", "-a"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            return True, "Shutdown cancelled successfully."

        error_msg = result.stderr.strip() or "No shutdown in progress."
        return False, error_msg
    except Exception as exc:
        logger.error(f"Cancel shutdown failed: {exc}")
        return False, str(exc)


def execute_sleep() -> tuple[bool, str]:
    try:
        command = [
            "powershell",
            "-NoProfile",
            "-Command",
            (
                "$signature = '[DllImport(\"powrprof.dll\", SetLastError = true)] "
                "public static extern bool SetSuspendState(bool hibernate, bool forceCritical, bool disableWakeEvent);'; "
                "Add-Type -Namespace Win32 -Name Power -MemberDefinition $signature; "
                "if ([Win32.Power]::SetSuspendState($false, $false, $false)) { exit 0 } else { exit 1 }"
            ),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            return True, "Sleep command executed successfully."

        error_msg = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        logger.error(f"Sleep command failed: {error_msg}")
        return False, error_msg
    except subprocess.TimeoutExpired:
        logger.error("Sleep command timeout")
        return False, "Command execution timeout."
    except Exception as exc:
        logger.error(f"Sleep command exception: {exc}")
        return False, str(exc)


@app.route("/", methods=["GET"])
@ip_whitelist_required
def home():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
@ip_whitelist_required
def login():
    if is_logged_in():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if Config.validate_login(username, password):
            session.clear()
            session["logged_in"] = True
            session["username"] = username
            session.permanent = True
            logger.info(f"{log_prefix()} Login success - IP: {client_ip()}, User: {username}")
            next_path = request.args.get("next") or url_for("dashboard")
            return redirect(next_path)

        logger.warning(f"{log_prefix()} Login failed - IP: {client_ip()}, User: {username}")
        flash("账号或密码错误。", "error")

    return render_template("login.html")


@app.route("/logout", methods=["POST"])
@ip_whitelist_required
@login_required
def logout():
    username = session.get("username", "")
    logger.info(f"{log_prefix()} Logout - IP: {client_ip()}, User: {username}")
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard", methods=["GET"])
@ip_whitelist_required
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        username=session.get("username", ""),
        host=request.host,
        whitelist_enabled=bool(Config.get_ip_whitelist()),
    )


@app.route("/service-worker.js", methods=["GET"])
def service_worker():
    return send_from_directory("static", "service-worker.js")


@app.route("/actions/shutdown", methods=["POST"])
@ip_whitelist_required
@login_required
def web_shutdown():
    delay, schedule_text = resolve_shutdown_delay(request.form)
    force = parse_force(request.form.get("force", False))

    logger.info(
        f"{log_prefix()} Web shutdown request - IP: {client_ip()}, Delay: {delay}s, Force: {force}"
    )
    success, message = execute_shutdown(delay, force)

    if success:
        flash(f"已提交关机，{schedule_text}", "success")
    else:
        flash(f"关机失败：{message}", "error")

    return redirect(url_for("dashboard"))


@app.route("/actions/cancel", methods=["POST"])
@ip_whitelist_required
@login_required
def web_cancel_shutdown():
    logger.info(f"{log_prefix()} Web cancel request - IP: {client_ip()}")
    success, message = execute_cancel_shutdown()

    if success:
        flash("已取消关机。", "success")
    else:
        flash(f"取消失败：{message}", "error")

    return redirect(url_for("dashboard"))


@app.route("/actions/sleep", methods=["POST"])
@ip_whitelist_required
@login_required
def web_sleep():
    logger.info(f"{log_prefix()} Web sleep request - IP: {client_ip()}")
    success, message = execute_sleep()

    if success:
        flash("已提交睡眠。", "success")
    else:
        flash(f"睡眠失败：{message}", "error")

    return redirect(url_for("dashboard"))


@app.route("/api/system/shutdown", methods=["POST"])
@ip_whitelist_required
@login_required
def api_shutdown():
    if not request.is_json:
        return jsonify({"code": 400, "message": "Request must be JSON format."}), 400

    data = request.get_json(silent=True) or {}
    delay = parse_delay(data.get("delay", 0))
    force = parse_force(data.get("force", False))

    logger.info(
        f"{log_prefix()} API shutdown request - IP: {client_ip()}, Delay: {delay}s, Force: {force}"
    )
    success, message = execute_shutdown(delay, force)

    if success:
        response_msg = (
            f"System will shutdown in {delay} seconds."
            if delay > 0
            else "System is shutting down now."
        )
        return jsonify({"code": 200, "message": response_msg}), 200

    return jsonify({"code": 500, "message": f"Command execution failed: {message}"}), 500


@app.route("/api/system/cancel", methods=["POST"])
@ip_whitelist_required
@login_required
def api_cancel_shutdown():
    logger.info(f"{log_prefix()} API cancel request - IP: {client_ip()}")
    success, message = execute_cancel_shutdown()

    if success:
        return jsonify({"code": 200, "message": message}), 200
    return jsonify({"code": 400, "message": message}), 400


@app.route("/api/system/sleep", methods=["POST"])
@ip_whitelist_required
@login_required
def api_sleep():
    logger.info(f"{log_prefix()} API sleep request - IP: {client_ip()}")
    success, message = execute_sleep()

    if success:
        return jsonify({"code": 200, "message": message}), 200
    return jsonify({"code": 500, "message": message}), 500


@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify(
        {
            "code": 200,
            "message": "Service is running.",
            "timestamp": datetime.now().isoformat(),
        }
    ), 200


if __name__ == "__main__":
    try:
        Config.validate()
        logger.info(f"Service starting... listen on {Config.HOST}:{Config.PORT}")
        serve(
            app,
            host=Config.HOST,
            port=Config.PORT,
        )
    except ValueError as exc:
        logger.error(f"Config error: {exc}")
        print(f"\nError: {exc}")
        print("Please update .env with valid settings.")
