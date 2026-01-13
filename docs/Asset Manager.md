### Technical Documentation: Asset Manager Component

This document defines the **Asset Service**, the atomic "Warehouse" of the system. Its primary directive is to manage the lifecycle of data, bridging the gap between database metadata and physical storage. It maintains a strict state machine to allow for "Data Promises" (Pipeline Enqueueing).

---

#### 1. Component Scope

* **Responsibilities:**
* Unified storage of `FILE` types (Disk) and `VALUE` types (Database).
* State management of Assets (`PENDING` -> `AVAILABLE` -> `FAILED`).
* Generating the **Standardized Input Manifest** for Module execution.
* Auto-resolution of database values into temporary files for CLI compatibility.


* **Strict Non-Responsibilities:**
* The Asset Service does **not** know how to run tasks.
* It does **not** validate if a file is "correct" for a module (The Orchestrator does this).



---

#### 2. Data Models (MongoDB)

**Collection:** `assets`
This record is the "Single Source of Truth" for any piece of data in the system.

| Field | Type | Description |
| --- | --- | --- |
| `_id` | UUID | Unique identifier used for all task mappings. |
| `label` | String | Human-readable name (e.g., "Input_Video.mp4"). |
| `status` | Enum | `PENDING`, `AVAILABLE`, `FAILED`. |
| `type` | Enum | `FILE` (on disk) or `VALUE` (in DB). |
| `media_type` | String | MIME type (e.g., `video/mp4`, `text/plain`, `application/json`). |
| `storage_path` | String | Absolute path on disk (Null if type is `VALUE` or status is `PENDING`). |
| `value_content` | Mixed | Raw data (e.g., transcript string) if type is `VALUE`. |
| `created_by_task` | UUID | Reference to the Task ID that is promised to produce this asset. |
| `tags` | Array | Metadata for filtering (e.g., `["raw-upload", "user-id-5"]`). |

---

#### 3. State Machine Logic

The Asset Service enables asynchronous workflows through a strict state transition:

1. **Creation (Promise):** When a task is queued, the Asset Service creates a record with `status: PENDING`.
2. **Referencing:** Subsequent tasks are created by referencing this `_id`. They are "blocked" by the Orchestrator because the status is not yet `AVAILABLE`.
3. **Fulfillment:** When a module finishes execution, it saves its output. The Asset Service moves the file to the final directory, updates `storage_path`, and flips status to `AVAILABLE`.
4. **Failure:** If a task crashes, the Asset Service flips the status to `FAILED`, signaling all dependent tasks to cancel or wait.

---

#### 4. API Interface (Internal Service Layer)

The `AssetManager` class provides the following atomic methods:

* **`create_upload_asset(file_path, label, media_type)`**: Registers a file already present on the server (e.g., via multipart upload). Sets status to `AVAILABLE`.
* **`create_pending_asset(task_id, label, media_type)`**: Reserves a spot for a future result. Returns the `asset_id`.
* **`fulfill_asset(asset_id, actual_file_path)`**: The "Success" trigger. Moves the file to `/data/generated/{task_id}/` and updates DB.
* **`get_manifest_path(asset_mappings, config_params)`**:
* Iterates through the requested Asset IDs.
* If an asset is a `VALUE`, it writes it to a `.txt` or `.json` file in a temporary directory.
* Returns the path to a generated `input_data.json` which contains a map of keys to absolute file paths.



---

#### 5. Directory Structure (Storage)

To maintain order on the host machine, the Asset Service enforces this hierarchy:

```text
/storage/
├── uploads/                # Primary ingestion for user files
│   └── YYYY-MM-DD/
└── generated/              # Output from Task Modules
    └── {task_id}/          # Isolated per task to avoid filename collisions
        └── output_v1.mp4

```

---

#### 6. Tech Stack Recommendations

* **Database:** MongoDB (Current shared infrastructure).
* **File Handling:** Python `shutil` for atomic moves and `tempfile` for the Value-to-File bridge.
* **Path Management:** `pathlib` for cross-platform (Windows/Linux) compatibility.
