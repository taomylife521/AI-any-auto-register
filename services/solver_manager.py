"""Turnstile Solver 进程管理 - 后端启动时自动拉起"""
import subprocess
import sys
import os
import time
import threading
import requests

SOLVER_PORT = 8889
SOLVER_URL = f"http://localhost:{SOLVER_PORT}"
_proc: subprocess.Popen = None
_lock = threading.Lock()


def is_running() -> bool:
    try:
        r = requests.get(f"{SOLVER_URL}/", timeout=2)
        return r.status_code < 500
    except Exception:
        return False


def start():
    global _proc
    with _lock:
        if is_running():
            print("[Solver] 已在运行")
            return
        # PyInstaller 打包后 sys.executable 指向 backend 可执行文件，
        # 用 --solver 参数让它走 solver 入口；源码模式下走 python + start.py
        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--solver",
                   "--browser_type", "camoufox",
                   "--thread", "1",
                   "--port", str(SOLVER_PORT)]
        else:
            solver_script = os.path.join(
                os.path.dirname(__file__), "turnstile_solver", "start.py"
            )
            cmd = [sys.executable, solver_script,
                   "--browser_type", "camoufox",
                   "--thread", "1",
                   "--port", str(SOLVER_PORT)]
        _proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        # 等待服务就绪（最多30s）
        for _ in range(30):
            time.sleep(1)
            if is_running():
                print(f"[Solver] 已启动 PID={_proc.pid}")
                return
        print("[Solver] 启动超时")


def stop():
    global _proc
    with _lock:
        if _proc and _proc.poll() is None:
            _proc.terminate()
            _proc.wait(timeout=5)
            print("[Solver] 已停止")
            _proc = None


def start_async():
    """在后台线程启动，不阻塞主进程"""
    t = threading.Thread(target=start, daemon=True)
    t.start()
