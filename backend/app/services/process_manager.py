# process_manager.py
import asyncio
import subprocess
import threading
import os
import shlex
import time
from typing import Dict, Any, Optional
from app.services.model_optimizer import model_optimizer, process_manager as optimizer_process_manager

# structure to track running jobs per session_id
running_jobs: Dict[str, Dict[str, Any]] = {}
# each job dict example:
# {
#   "type": "local" or "api",
#   "proc": Popen object (for local),
#   "task": asyncio.Task (for api),
#   "queue": asyncio.Queue (for logs),
#   "started_at": timestamp,
#   "meta": {...}
# }

def create_log_queue():
    return asyncio.Queue()

# ---------- Local model execution ----------
def start_local_process(session_id: str, model_path: str, runtime: str = "auto", extra_args: Optional[list] = None) -> Dict[str, Any]:
    """
    Start a subprocess for a local model run with automatic runtime detection.
    Returns job metadata.
    """
    if session_id in running_jobs:
        raise RuntimeError("Session already has a running job")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    queue = create_log_queue()

    # Build command based on runtime
    cmd = build_model_command(model_path, runtime, extra_args or [])

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,
        universal_newlines=True
    )

    # start thread to read stdout and push to asyncio queue
    def _reader_thread(p, q):
        try:
            for line in p.stdout:
                # push line to asyncio queue (non-blocking)
                # Store the future to prevent warnings, but don't await it
                future = asyncio.run_coroutine_threadsafe(q.put(line.rstrip("\n")), asyncio.get_event_loop())
                # Store the future to prevent it from being garbage collected too early
                _ = future
        except Exception as e:
            try:
                future = asyncio.run_coroutine_threadsafe(q.put(f"[reader-error] {e}"), asyncio.get_event_loop())
                _ = future
            except Exception:
                pass

    t = threading.Thread(target=_reader_thread, args=(proc, queue), daemon=True)
    t.start()

    job = {
        "type": "local",
        "proc": proc,
        "queue": queue,
        "thread": t,
        "cmd": cmd,
        "model_path": model_path,
        "runtime": runtime,
        "started_at": time.time()
    }
    running_jobs[session_id] = job
    return {"status": "started", "pid": proc.pid, "session_id": session_id, "cmd": cmd}

def build_model_command(model_path: str, runtime: str, extra_args: list) -> list:
    """Build the llama.cpp command based on runtime and model path"""
    # Base command with model path
    base_cmd = ["./llama.cpp/build/bin/llama-cli", "-m", model_path]
    
    # Add runtime-specific flags
    if runtime == "cuda":
        # Use CUDA with maximum GPU layers
        base_cmd.extend(["--ngl", "999", "--cuda"])
    elif runtime == "metal":
        # Use Metal with 1 GPU layer (typical for Apple Silicon)
        base_cmd.extend(["--ngl", "1", "--metal"])
    elif runtime == "cpu":
        # CPU-only mode
        base_cmd.extend(["--no-metal", "--ngl", "0"])
    else:  # auto
        # Let llama.cpp auto-detect best runtime
        base_cmd.extend(["--ngl", "auto"])
    
    # Add any extra arguments
    base_cmd.extend(extra_args)
    
    return base_cmd

def stop_local_process(session_id: str) -> Dict[str, Any]:
    job = running_jobs.get(session_id)
    if not job or job.get("type") != "local":
        return {"status": "no_local_job"}
    proc: subprocess.Popen = job["proc"]
    try:
        proc.terminate()  # gentle
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()   # force
    except Exception as e:
        return {"status": "error", "error": str(e)}
    # cleanup
    queue: asyncio.Queue = job["queue"]
    asyncio.run_coroutine_threadsafe(queue.put("[process-stopped]"), asyncio.get_event_loop())
    del running_jobs[session_id]
    return {"status": "stopped"}

# ---------- API model execution (async cancellable task) ----------
import aiohttp
import time

async def _api_runner(session_id: str, api_info: Dict[str, Any]):
    """
    Example API runner which streams data from an API and writes to queue.
    api_info may include: url, headers, payload
    """
    queue: asyncio.Queue = running_jobs[session_id]["queue"]
    try:
        url = api_info["url"]
        headers = api_info.get("headers", {})
        payload = api_info.get("payload", {})
        timeout = aiohttp.ClientTimeout(total=None)
        async with aiohttp.ClientSession(timeout=timeout) as client:
            # example: POST and stream lines (depends on vendor API)
            async with client.post(url, headers=headers, json=payload) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    await queue.put(f"[api-error] status={resp.status} body={text}")
                else:
                    # stream text chunks
                    async for chunk, _ in resp.content.iter_chunks():
                        if chunk:
                            text = chunk.decode(errors="ignore")
                            # push text
                            await queue.put(text)
        await queue.put("[api-finished]")
    except asyncio.CancelledError:
        await queue.put("[api-cancelled]")
        raise
    except Exception as e:
        await queue.put(f"[api-exception] {e}")
    finally:
        # remove job if still present
        if session_id in running_jobs:
            running_jobs.pop(session_id, None)

def start_api_task(session_id: str, api_info: Dict[str, Any]) -> Dict[str, Any]:
    if session_id in running_jobs:
        raise RuntimeError("Session already has a running job")
    queue = create_log_queue()
    job = {"type": "api", "queue": queue}
    running_jobs[session_id] = job
    loop = asyncio.get_event_loop()
    task = loop.create_task(_api_runner(session_id, api_info))
    job["task"] = task
    return {"status": "started", "task_id": id(task)}

def stop_api_task(session_id: str) -> Dict[str, Any]:
    job = running_jobs.get(session_id)
    if not job or job.get("type") != "api":
        return {"status": "no_api_job"}
    task: asyncio.Task = job["task"]
    task.cancel()
    # queue will get cancelled message from coroutine
    return {"status": "cancelled"}

# ---------- Generic helpers ----------
def stop_job(session_id: str) -> Dict[str, Any]:
    job = running_jobs.get(session_id)
    if not job:
        return {"status":"no_job"}
    t = job["type"]
    if t == "local":
        return stop_local_process(session_id)
    elif t == "api":
        return stop_api_task(session_id)
    else:
        return {"status": "unknown_type"}

def get_job_status(session_id: str) -> Dict[str, Any]:
    job = running_jobs.get(session_id)
    if not job:
        return {"status":"no_job"}
    if job["type"] == "local":
        proc = job["proc"]
        alive = proc.poll() is None
        return {"type":"local","alive":alive,"pid":proc.pid}
    else:
        task = job.get("task")
        return {"type":"api", "done":task.done() if task else True}

def get_job_queue(session_id: str) -> Optional[asyncio.Queue]:
    job = running_jobs.get(session_id)
    if not job:
        return None
    return job["queue"]

# ---------- Enhanced process management with graceful fallback ----------
async def start_optimized_local_process(session_id: str, model_path: str, extra_args: Optional[list] = None) -> Dict[str, Any]:
    """
    Start a local model process with optimized configuration and graceful fallback
    """
    if session_id in running_jobs:
        raise RuntimeError("Session already has a running job")

    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model file not found: {model_path}")

    # Get optimized runtime configuration
    config = model_optimizer.get_optimized_runtime_config(model_path)
    
    # Determine optimal runtime based on configuration
    if config["use_gpu"]:
        runtime = "metal" if model_optimizer.apple_silicon.is_apple_silicon else "cuda"
    else:
        runtime = "cpu"
        # Log fallback reason
        print(f"🔧 {config['fallback_reason']}")

    queue = create_log_queue()

    # Build command with optimized runtime
    cmd = build_optimized_model_command(model_path, runtime, extra_args or [], config)

    # Use the enhanced process manager with timeout handling
    result = await optimizer_process_manager.run_with_timeout(cmd, session_id, config)
    
    if result["success"]:
        # Process completed successfully
        job = {
            "type": "local_optimized",
            "queue": queue,
            "cmd": cmd,
            "model_path": model_path,
            "runtime": runtime,
            "config": config,
            "started_at": time.time(),
            "result": result
        }
        running_jobs[session_id] = job
        
        # Push result to queue
        if result["stdout"]:
            for line in result["stdout"].split('\n'):
                if line.strip():
                    asyncio.run_coroutine_threadsafe(queue.put(line), asyncio.get_event_loop())
        
        return {
            "status": "completed",
            "session_id": session_id,
            "runtime": runtime,
            "config": config,
            "output": result["stdout"]
        }
    else:
        # Process failed or timed out
        error_msg = result.get("error", "Unknown error")
        return {
            "status": "error",
            "session_id": session_id,
            "error": error_msg,
            "config": config
        }

def build_optimized_model_command(model_path: str, runtime: str, extra_args: list, config: Dict) -> list:
    """Build optimized llama.cpp command based on configuration"""
    # Base command with model path
    base_cmd = ["./llama.cpp/build/bin/llama-cli", "-m", model_path]
    
    # Add runtime-specific flags based on optimization
    if runtime == "cuda":
        base_cmd.extend(["--ngl", "999", "--cuda"])
    elif runtime == "metal":
        # Use Metal with optimized GPU layers
        if config["use_gpu"]:
            base_cmd.extend(["--ngl", "1", "--metal"])
        else:
            base_cmd.extend(["--no-metal", "--ngl", "0"])
    elif runtime == "cpu":
        base_cmd.extend(["--no-metal", "--ngl", "0"])
    else:  # auto
        base_cmd.extend(["--ngl", "auto"])
    
    # Add any extra arguments
    base_cmd.extend(extra_args)
    
    return base_cmd

async def stop_optimized_process(session_id: str) -> Dict[str, Any]:
    """Stop an optimized process gracefully"""
    # Try to kill via the enhanced process manager first
    killed = optimizer_process_manager.kill_process(session_id)
    
    # Also try the traditional method
    job = running_jobs.get(session_id)
    if job and job.get("type") == "local_optimized":
        # Clean up the job entry
        queue: asyncio.Queue = job["queue"]
        asyncio.run_coroutine_threadsafe(queue.put("[process-stopped]"), asyncio.get_event_loop())
        del running_jobs[session_id]
    
    return {
        "status": "stopped" if killed else "not_found",
        "session_id": session_id
    }

def get_optimized_process_status(session_id: str) -> Dict[str, Any]:
    """Get status of an optimized process"""
    # Check enhanced process manager first
    running_sessions = optimizer_process_manager.get_running_processes()
    is_running = session_id in running_sessions
    
    job = running_jobs.get(session_id)
    if job and job.get("type") == "local_optimized":
        return {
            "type": "local_optimized",
            "running": is_running,
            "runtime": job.get("runtime", "unknown"),
            "config": job.get("config", {}),
            "started_at": job.get("started_at", 0)
        }
    
    return {"status": "no_job"}

# ---------- Convenience functions for backward compatibility ----------
def get_supported_quants() -> list:
    """Get list of supported quantization types"""
    return list(model_optimizer.DEFAULT_SUPPORTED_QUANTS.keys())

def should_use_cpu_fallback(model_path: str) -> tuple:
    """Check if CPU fallback should be used"""
    return model_optimizer.should_use_cpu_fallback(model_path)
