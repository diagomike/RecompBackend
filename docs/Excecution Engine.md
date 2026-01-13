### Technical Specification: The Execution Engine

**Version:** 1.0.0
**Component:** Task Runner Core / Execution Engine

#### 1. Overview

The **Execution Engine** (or "The Muscle") is the final atomic component. It is a stateless consumer responsible for picking up "QUEUED" tasks, preparing their runtime environment, executing the logic, and ensuring the result is reliably handed back to the Asset Service.

It **never** makes decisions. It only follows orders from the Orchestrator (via the Queue) and uses the Registry (for tools) and Asset Service (for materials).

#### 2. Scope of Responsibilities

* **Queue Consumption:** Polling the database/queue for tasks with status `QUEUED`.
* **Environment Preparation:** Ensuring the module's `venv` is active and valid.
* **Manifest Generation:** Calling the Asset Service to materialize the `input_manifest.json` (resolving paths and creating temp config files).
* **Process Isolation:** Spawning the child process (via the Registry's standardized CLI) to bypass the GIL and ensure isolation.
* **Outcome Handling:**
* **Success:** Detecting the exit code `0`, finding the output files, and calling `AssetService.fulfill_promise()`.
* **Failure:** Detecting non-zero exit codes or timeouts, capturing `stderr`, and updating the Task record with logs.



---

#### 3. The Execution Lifecycle (The "Run" Loop)

The Engine operates in an infinite loop (or as a triggered Cron/Daemon):

1. **Poll:** Fetch one task: `find_one_and_update({ status: "QUEUED" }, { $set: { status: "RUNNING", started_at: Now } })`.
2. **Prepare:**
* Load Task Data (`input_map`, `module_id`).
* **Call Asset Service:** `get_manifest_path(input_map, config)` → Returns `/tmp/task_888/input.json`.


3. **Execute:**
* **Call Registry Runner:** `run_module(module_id, manifest_path)`.
* *Note: This blocks the worker thread until the external process finishes.*


4. **Finalize:**
* **If Success:**
* Read the Module's `output_manifest.json` (optional, or we assume standardized output paths).
* For each output asset promised in `output_map`:
* Locate the file (e.g., `/data/generated/task_888/video.mp4`).
* **Call Asset Service:** `fulfill_promise(asset_id, path)`.


* Update Task Status: `COMPLETED`.


* **If Error:**
* Capture `stderr` log.
* Update Task Status: `FAILED`.
* (Crucial) **Call Asset Service:** `fail_promise(asset_id)` (This prevents downstream tasks from waiting forever).





---

#### 4. Failure Handling & Resilience

* **Timeouts:** The Engine must enforce a `max_runtime` (e.g., 1 hour). If exceeded, `kill` the subprocess.
* **Zombie Tasks:** If the Engine crashes *while* running a task, the task remains `RUNNING` forever.
* *Solution:* On startup, the Engine checks for tasks marked `RUNNING` with `started_at > 2 hours` and resets them to `QUEUED` (or fails them).



---

#### 5. API Interface (Internal)

The `ExecutionService` is mostly an internal looper, but exposes:

* `start_worker()`: Begins the polling loop.
* `stop_worker()`: Graceful shutdown (finishes current task, then stops).

---

#### 6. Integration Map (The Final Picture)

| Component | Role | Interaction |
| --- | --- | --- |
| **Orchestrator** | **Commander** | Puts tasks in `QUEUED`. Engine takes them out. |
| **Asset Service** | **Supplier** | Provides paths to inputs; Accepts final output files. |
| **Registry** | **Toolbox** | Provides the `venv` and the command to run. |

