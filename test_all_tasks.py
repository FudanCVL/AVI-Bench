"""
Test script: run N samples per task to verify all tasks work end-to-end.
Each task runs in a separate subprocess to prevent CUDA state cascade failures.

Usage:
    CUDA_VISIBLE_DEVICES=0,1 python test_all_tasks.py
Override defaults via env:
    MODEL_PATH=... DATA_ROOT=... N_TEST=5 python test_all_tasks.py
"""
import os
import sys
import json
import subprocess

from scripts.definitions import TASK_TO_CATEGORY

N_TEST = int(os.environ.get("N_TEST", 5))
MODEL_PATH = os.environ.get("MODEL_PATH", "gemini-2.5-pro")
DATA_ROOT = os.environ.get("DATA_ROOT", "./data/levels")
WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test_one_task.py')


def run_task_subprocess(task_name):
    """Run a single task test in an isolated subprocess."""
    env = os.environ.copy()
    cmd = [
        sys.executable, WORKER, task_name,
        str(N_TEST), MODEL_PATH, DATA_ROOT,
    ]

    proc = subprocess.run(
        cmd, capture_output=True, text=True, env=env,
        cwd=os.path.dirname(os.path.abspath(__file__)),
        timeout=600,
    )

    stdout = proc.stdout.strip()
    stderr = proc.stderr

    if proc.returncode != 0 and not stdout:
        return "FAIL", f"subprocess crashed (rc={proc.returncode}): {stderr[-500:]}"

    try:
        result = json.loads(stdout.split('\n')[-1])
        return result['status'], result.get('results', result.get('detail', ''))
    except (json.JSONDecodeError, KeyError, IndexError):
        return "FAIL", f"bad output: {stdout[-200:]} | stderr: {stderr[-300:]}"


if __name__ == '__main__':
    all_tasks = list(TASK_TO_CATEGORY.keys())
    summary = []

    print("=" * 60)
    print(f"Testing {len(all_tasks)} tasks, {N_TEST} samples each")
    print(f"Each task runs in isolated subprocess")
    print("=" * 60)

    for task_name in all_tasks:
        print(f"\n--- Testing {task_name} ({N_TEST} samples) ---")
        try:
            status, detail = run_task_subprocess(task_name)
        except subprocess.TimeoutExpired:
            status, detail = "FAIL", "timeout (600s)"
        except Exception as e:
            status, detail = "FAIL", str(e)

        if status == "OK":
            print(f"  [{status}] predictions:")
            for i, pred in enumerate(detail):
                preview = (pred[:80] if pred else "None")
                print(f"    [{i}] {preview}")
        else:
            print(f"  [{status}] {detail}")

        summary.append((task_name, status))

    print("\n" + "=" * 60)
    print("SUMMARY:")
    for task_name, status in summary:
        print(f"  {task_name:10s} {status}")
    ok = sum(1 for _, s in summary if s == "OK")
    print(f"\n{ok}/{len(summary)} tasks passed.")
