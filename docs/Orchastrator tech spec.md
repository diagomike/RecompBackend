### Technical Specification: The Orchestrator Component

**Version:** 1.0.0
**Component:** Task Runner Core / Orchestrator

#### 1. Overview

The **Orchestrator** acts as the central nervous system ("The Brain") of the application. It is strictly separated from execution logic. Its role is to validatate user intent against system contracts, manage the state of tasks, and resolve the complex dependency graph created by "Pending Assets."

It ensures that no task ever enters the execution queue unless all its requirements (Assets and Resources) are strictly met.

#### 2. Scope of Responsibilities

* **Contract Enforcement:** Validates every Task Creation Request against the Module's defined Interface (stored in the Registry).
* **Asset Allocation:** Commands the Asset Service to reserve "Pending Assets" for the task's future outputs.
* **Dependency Resolution:** Identifies if input assets are `PENDING`. If so, marks the task as `BLOCKED`.
* **State Transition:** Watches for Asset Availability events to promote tasks from `BLOCKED` → `QUEUED`.

---

#### 3. Data Models (MongoDB)

**Collection:** `tasks`
This collection represents the "Work Order."

| Field | Type | Description |
| --- | --- | --- |
| `_id` | UUID | Unique Task Identifier. |
| `module_id` | String | Reference to the Registry Module ID (e.g., `face-detect-v1`). |
| `status` | Enum | `CREATED`, `BLOCKED`, `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`. |
| `input_map` | Object | Map of Module Input Keys -> Asset IDs. `{ "source_video": "asset_123" }` |
| `output_map` | Object | Map of Module Output Keys -> Asset IDs. `{ "faces_zip": "asset_456" }` |
| `config` | Object | Runtime configuration (e.g., `{"priority": "high"}`). |
| `blocking_assets` | Array | List of Asset IDs this task is waiting for. |
| `created_at` | Date | Timestamp. |
| `error_log` | String | If failed, the reason why. |

---

#### 4. Operational Workflow

The Orchestrator implements a strict 3-step pipeline for task submission.

**A. Step 1: Pre-Flight Validation (The "Contract Check")**

* **Trigger:** User/API submits a request `POST /tasks`.
* **Logic:**
1. **Fetch Contract:** Retrieve `module.json` schema from the **Module Registry**.
2. **Iterate Inputs:** For every input defined in the contract:
* Check if the user provided an Asset ID.
* **Query Asset Service:** Get metadata for that Asset ID.
* **Type Mismatch Check:** If Module asks for `video/mp4` and Asset is `audio/wav` → **REJECT**.
* **Status Check:** If Asset status is `FAILED` → **REJECT**.
* **Availability Check:** If Asset status is `PENDING`, add ID to `blocking_assets` list.





**B. Step 2: Asset Reservation (The "Promise")**

* **Logic:**
1. **Iterate Outputs:** For every output defined in the contract:
* Call **Asset Service** to create a `PENDING` asset.
* Receive the new `asset_id`.


2. **Construct Task Record:** Save the mapping of Input IDs and valid Output IDs.



**C. Step 3: State Determination (The "Traffic Light")**

* **Logic:**
* If `blocking_assets` is empty `[]` → Set status `QUEUED` (Ready for Execution Engine).
* If `blocking_assets` has items → Set status `BLOCKED`.



---

#### 5. Dependency Resolution Logic (The Un-Blocker)

This is the critical "Reconciliation Loop" that prevents deadlocks.

**Trigger:** Event `AssetBecameAvailable(asset_id)`
*(This event is fired by the Asset Service when a file is successfully finalized).*

**Logic:**

1. **Find Dependents:** Query `tasks` collection: `find({ status: "BLOCKED", blocking_assets: asset_id })`.
2. **Update:** For each found task, remove `asset_id` from its `blocking_assets` array.
3. **Re-Evaluate:**
* If `blocking_assets` is now empty → Update status to `QUEUED`.
* (Optional) Push to the Worker Queue immediately.



---

#### 6. API Interface (Internal & External)

The `OrchestratorService` class exposes these atomic methods:

* **`validate_and_create_task(module_id, input_asset_map)`**:
* The primary entry point. Returns `task_id` and the list of generated output `asset_ids`.


* **`get_task_status(task_id)`**:
* Returns current state and, if blocked, *what* it is waiting for (e.g., `"Waiting on Asset X from Task Y"`).


* **`handle_asset_event(event_type, asset_id)`**:
* Internal method called by the Asset Service to trigger unblocking.


* **`get_queue_head()`**:
* Called by the Execution Engine to get the next `QUEUED` task (sorted by priority/time).



---

#### 7. Integration Map

| Component | Interaction | Data Flow |
| --- | --- | --- |
| **Module Registry** | **Read-Only** | Orchestrator reads `module.json` to enforce types. |
| **Asset Service** | **Read/Write** | Orchestrator reads Asset Metadata (Validation) and writes `PENDING` requests. |
| **Execution Engine** | **Write-Only** | Orchestrator writes to the Queue; Engine reads from it. |

---

### Step 5: Confirmation

**Does this logic for the Orchestrator sound robust to you?**
If you agree, we have now defined the complete "Trinity":

1. **Registry:** The Toolset.
2. **Asset Manager:** The Data Warehouse.
3. **Orchestrator:** The Brain.

We can now proceed to generating the Python implementation for the **Asset Manager** and then the **Orchestrator**.