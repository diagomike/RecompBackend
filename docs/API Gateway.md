### 🟢 System Status: API Ingress Architecture Defined

To maintain the **Atomic Composition** philosophy, we must treat the API Layer not as a "bucket for code," but as a **Stateless Gateway**.

The FastAPI implementation will use **APIRouters** to maintain strict isolation. No business logic (processing, DB queries, or file manipulation) shall live in the route handlers. Instead, the routes will act as thin wrappers that call the `Service` classes we have already defined.

---

### Technical Specification: The API Gateway (FastAPI)

#### 1. Component Scope

* **Responsibilities:**
* Request Validation (using Pydantic models).
* Authentication and Authorization (RBAC).
* Routing requests to the appropriate Atomic Service.
* Standardizing JSON response formats.


* **Strict Non-Responsibilities:**
* The API does **not** move files (it calls the Asset Service).
* The API does **not** manage the queue (it calls the Orchestrator).
* The API does **not** execute ML models (it calls the Execution Engine).



---

#### 2. Structural Blueprint (The "Atomic" Router Pattern)

The project structure will follow a modular router pattern. This allows us to scale the API without creating a "spaghetti" `main.py`.

```text
src/api/
├── main.py                 # The FastAPI Entry Point
├── dependencies.py         # Auth, DB Sessions, Service Singletons
└── routers/
    ├── modules.py          # Interface for the Module Registry
    ├── assets.py           # Interface for the Asset Service
    └── tasks.py            # Interface for the Orchestrator

```

---

#### 3. API Surface Area (Endpoint Mapping)

**A. Registry Endpoints (`/modules`)**

* `GET /modules`: Returns all `AVAILABLE` modules and their contracts (`inputs`/`outputs`).
* `GET /modules/{id}`: Returns the full contract for a specific tool.
* `POST /modules/scan`: Triggers a background scan for new module folders (Admin only).

**B. Asset Service Endpoints (`/assets`)**

* `POST /assets/upload`: Accepts multipart/form-data for new files.
* `GET /assets/{id}`: Returns asset metadata.
* `GET /assets/{id}/stream`: Streams the file content (Video/Image/Audio).
* `GET /assets`: List and filter assets by tag, label, or status.

**C. Orchestrator Endpoints (`/tasks`)**

* `POST /tasks`: Accepts a `module_id` and an `input_mapping`.
* `GET /tasks/{id}`: Returns the current state (`BLOCKED`, `QUEUED`, `RUNNING`, etc.).
* `GET /tasks/{id}/logs`: Returns stdout/stderr from the execution engine.
* `DELETE /tasks/{id}`: Cancels a queued or running task.

---

### Phase 2: Interrogation (Gap Analysis)

Before we finalize this specification, I need to grill you on the operational logic of the API layer:

1. **Authentication:** How do we identify users? Since Assets belong to someone, do we need a `User` entity to prevent User A from seeing User B's videos?
2. **Pagination:** "Heavy-duty" systems eventually have thousands of assets and tasks. Should we enforce pagination (`?limit=50&offset=0`) on all `GET` list endpoints from Day 1?
3. **Real-Time Feedback:** Since tasks are long-running, the frontend will need updates. Should we use **WebSockets** for status changes, or will the frontend **Poll** the `GET /tasks/{id}` endpoint every few seconds?
4. **CORS:** Which domains will the frontend be hosted on? (Security requirement for FastAPI middleware).

---

### Phase 3: Technical Feasibility Report

* **Viability:** **High.** FastAPI’s asynchronous nature is perfect for this. It can handle incoming file uploads and API requests while the "Heavy Duty" work happens in separate OS processes managed by the Execution Engine.
* **Bottleneck:** The main bottleneck will be **File Streaming**. If 100 users try to watch 4K videos at once, the API server's network bandwidth will saturate. We may eventually need a separate "Media Server," but for now, FastAPI can handle it.

-----------------------------------------------

### Technical Specification: The API Gateway (FastAPI)

**Version:** 1.0.0
**Component:** Task Runner Core / Gateway API
**Philosophy:** This component serves as the **Stateless Interface**. It maintains no internal state; it purely validates incoming requests against the **Module Contracts** and routes them to the Asset Service or Orchestrator.

---

#### 1. Component Scope

* **Purpose:** To provide a unified RESTful interface for external clients (Frontend/Mobile/3rd Party).
* **Atomic Boundary:** It does not interact with the file system or the execution engine directly. It communicates with the internal service classes (`AssetManager`, `RegistryOrchestrator`, `TaskOrchestrator`).
* **Validation:** Every request is strictly validated using **Pydantic V2** models to ensure the data matches the contracts before it touches the database.

---

#### 2. Data Models (Pydantic Schemas)

To ensure the "Contract" is enforced, we define strict request/response schemas.

**A. Task Submission Schema**

```python
class TaskCreateRequest(BaseModel):
    module_id: str
    # Map of input key defined in module.json to existing/pending Asset ID
    input_mapping: Dict[str, str] 
    # Optional parameters defined as "VALUE" in module.json
    config: Optional[Dict[str, Any]] = {}

```

**B. Asset Response Schema**

```python
class AssetResponse(BaseModel):
    id: str
    label: str
    status: Literal["PENDING", "AVAILABLE", "FAILED"]
    type: Literal["FILE", "VALUE"]
    media_type: str
    created_at: datetime

```

---

#### 3. API Interface (Endpoint Blueprint)

The API is divided into three logical routers.

| Tag | Method | Endpoint | Description |
| --- | --- | --- | --- |
| **Modules** | `GET` | `/modules` | Returns list of all verified/available modules. |
|  | `GET` | `/modules/{id}` | Returns the specific `inputs/outputs` contract for a tool. |
| **Assets** | `POST` | `/assets/upload` | Ingests a new file. Returns an `AVAILABLE` Asset ID. |
|  | `GET` | `/assets` | Paginated list of assets. Filters: `status`, `tag`. |
|  | `GET` | `/assets/{id}/download` | Redirects to the physical file path or streams data. |
| **Tasks** | `POST` | `/tasks` | **The Core Entry Point:** Validates mapping and enqueues. |
|  | `GET` | `/tasks/{id}` | Returns task status and associated `output_assets`. |
|  | `GET` | `/tasks/{id}/logs` | Streams `stdout/stderr` for debugging heavy tasks. |

---

#### 4. The "Pre-Flight" Validation Logic

When `POST /tasks` is called, the Gateway executes this atomic logic:

1. **Contract Retrieval:** Fetches the `module.json` from the Registry.
2. **Asset Verification:** For every `input_mapping` entry, it queries the Asset Service.
* If the ID doesn't exist → `404 Not Found`.
* If the Asset `media_type` doesn't match the Module's contract → `422 Unprocessable Entity`.


3. **Task Hand-off:** Only if valid, it calls `Orchestrator.create_task()`.

---

#### 5. Strategic Architectural Decisions (Based on Prime Directive)

* **Communication Style (Polling):** We will use **Short Polling** initially. The Frontend will query `GET /tasks/{id}` every 2–5 seconds. This avoids the stateful complexity of WebSockets, keeping the API gateway atomic and horizontally scalable.
* **Error Handling:** The API will return **RFC 7807 (Problem Details for HTTP APIs)** compliant JSON. If a heavy-duty task fails, the API will provide a clear error pointer (e.g., "Input 'source_video' is corrupted").
* **Pagination:** **Mandatory** on all `GET` list endpoints (Default: 20, Max: 100) to prevent memory exhaustion when the system scales to thousands of tasks.

---

#### 6. Tech Stack Recommendation

* **Framework:** FastAPI (Asynchronous, High Performance).
* **Web Server:** Uvicorn with Gunicorn workers.
* **Validation:** Pydantic V2.
* **Dependency Injection:** FastAPI `Depends` for providing singleton instances of `AssetManager` and `Orchestrator`.

---

### Step 5: Final Confirmation

This specification completes the architectural blueprint for your high-versatility task runner. Every sub-system is now defined:

1. **Module Registry:** The Toolbox.
2. **Asset Manager:** The Warehouse.
3. **Orchestrator:** The Brain.
4. **Execution Engine:** The Muscle.
5. **API Gateway:** The Interface.
