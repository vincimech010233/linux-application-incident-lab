"""Exercise healthy, misrouted, and recovered requests using a real Nginx."""

import argparse
import http.client
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from string import Template


ROOT = Path(__file__).resolve().parent


def unused_port(excluded):
    while True:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        if port not in excluded:
            excluded.add(port)
            return port


def get(port, path):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    try:
        connection.request("GET", path)
        response = connection.getresponse()
        return response.status, response.read().decode("utf-8", errors="replace")
    finally:
        connection.close()


def wait_for_status(port, path, expected, process):
    deadline = time.monotonic() + 4
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"service exited before HTTP {expected}")
        try:
            status, body = get(port, path)
            if status == expected:
                return status, body
        except (OSError, http.client.HTTPException):
            pass
        time.sleep(0.05)
    raise RuntimeError(f"service did not return HTTP {expected}")


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=3)


def run(nginx, manual=False):
    runtime = ROOT / ".runtime"
    runtime.mkdir(exist_ok=True)
    chosen = set()
    app_port = unused_port(chosen)
    proxy_port = unused_port(chosen)
    wrong_port = unused_port(chosen)
    template = Template((ROOT / "proxy/nginx.conf.template").read_text())
    results = {}

    with tempfile.TemporaryDirectory(prefix="scenario-", dir=runtime) as directory:
        work = Path(directory)
        with (work / "app.log").open("w") as app_log:
            app = subprocess.Popen(
                [sys.executable, "-u", str(ROOT / "app/server.py"), "--port", str(app_port)],
                stdout=app_log,
                stderr=subprocess.STDOUT,
                cwd=ROOT,
            )
            try:
                wait_for_status(app_port, "/health", 200, app)
                for name, upstream, expected in (
                    ("healthy", app_port, 200),
                    ("incident", wrong_port, 502),
                    ("recovered", app_port, 200),
                ):
                    mode = work / name
                    mode.mkdir()
                    config = mode / "nginx.conf"
                    error_log = mode / "error.log"
                    config.write_text(template.substitute(
                        pid_file=mode / "nginx.pid",
                        error_log=error_log,
                        access_log=mode / "access.log",
                        client_body_temp=mode / "client-body",
                        proxy_temp=mode / "proxy-temp",
                        fastcgi_temp=mode / "fastcgi-temp",
                        uwsgi_temp=mode / "uwsgi-temp",
                        scgi_temp=mode / "scgi-temp",
                        proxy_port=proxy_port,
                        upstream_port=upstream,
                    ))
                    config_check = subprocess.run(
                        [nginx, "-t", "-p", str(mode) + "/", "-c", str(config)],
                        capture_output=True,
                        text=True,
                        timeout=3,
                    )
                    if config_check.returncode != 0:
                        raise RuntimeError(f"nginx config check failed: {config_check.stderr}")
                    with (mode / "nginx.stdout").open("w") as nginx_stdout:
                        proxy = subprocess.Popen(
                            [nginx, "-p", str(mode) + "/", "-c", str(config), "-g", "daemon off;"],
                            stdout=nginx_stdout,
                            stderr=subprocess.STDOUT,
                            cwd=ROOT,
                        )
                        try:
                            status, body = wait_for_status(proxy_port, "/", expected, proxy)
                            upstream_health, _ = get(app_port, "/health")
                            results[name] = {"proxy_status": status, "upstream_health": upstream_health}
                            if expected == 200:
                                results[name]["response"] = body.strip()
                            if manual:
                                print(f"{name}: proxy http://127.0.0.1:{proxy_port}/ ; "
                                      f"upstream http://127.0.0.1:{app_port}/health", flush=True)
                                input("Run direct HTTP checks, then press Enter to continue: ")
                        finally:
                            stop(proxy)
                    if name == "incident":
                        results[name]["connection_refused_in_proxy_log"] = (
                            "connect() failed (111: Connection refused)" in error_log.read_text()
                        )
            finally:
                stop(app)

    return results


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--nginx", default=os.environ.get("NGINX_BIN") or shutil.which("nginx"))
    parser.add_argument("--manual", action="store_true", help="pause each state for operator HTTP checks")
    args = parser.parse_args()
    if not args.nginx or not Path(args.nginx).is_file():
        parser.error("provide an installed nginx binary with --nginx or NGINX_BIN")
    results = run(args.nginx, manual=args.manual)
    print(json.dumps(results, indent=2, sort_keys=True))
    if [results[name]["proxy_status"] for name in ("healthy", "incident", "recovered")] != [200, 502, 200]:
        raise SystemExit(1)
    if not results["incident"]["connection_refused_in_proxy_log"]:
        raise SystemExit("expected upstream connection refusal in nginx error log")


if __name__ == "__main__":
    main()
