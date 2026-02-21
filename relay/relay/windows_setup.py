import os
import platform
import subprocess
import sys


def _run(command):
    proc = subprocess.run(
        command,
        shell=True,
        text=True,
        capture_output=True,
    )
    return {
        "command": command,
        "returncode": proc.returncode,
        "stdout": (proc.stdout or "").strip(),
        "stderr": (proc.stderr or "").strip(),
        "ok": proc.returncode == 0,
    }


def bootstrap_windows(relay_port, app_dir=None):
    if platform.system().lower() != "windows":
        return {
            "ok": False,
            "message": "Windows bootstrap can only run on Windows.",
            "steps": [],
        }

    app_dir = app_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    python_exe = sys.executable
    relay_port = int(relay_port)

    firewall_name = f"POSRelay_{relay_port}"
    add_firewall = (
        "netsh advfirewall firewall add rule "
        f"name=\"{firewall_name}\" dir=in action=allow protocol=TCP localport={relay_port} profile=private"
    )

    task_name = "POSRelay_Autostart"
    task_command = (
        "schtasks /Create /F /SC ONLOGON "
        f"/TN \"{task_name}\" "
        f"/TR \"{python_exe} -m relay.app\""
    )

    steps = []
    steps.append(_run(add_firewall))
    steps.append(_run(task_command))

    all_ok = all(step["ok"] for step in steps)
    return {
        "ok": all_ok,
        "message": "Bootstrap completed" if all_ok else "Bootstrap completed with some errors",
        "relay_port": relay_port,
        "app_dir": app_dir,
        "python_exe": python_exe,
        "steps": steps,
    }

