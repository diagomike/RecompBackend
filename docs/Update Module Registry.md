
I think I forgot to create a way for the modules to specify what kind of data they need - a contract as it were so that in the UI, I will be required to assign the required input assets to create a task - but the assets are independent, the running modules are independent and it should probably the orchestrator that will handle this but Are you sure there will be no conflict - it think it will be ok if the orchestrator handles gathering data from the db and making sure the files exist and knowing what kind of data each function needs - or maybe the functions provide the kind of input data they need - (if contracts can be created independently then it is also OK )

what is the best way to go forward?

-------------------------------------------------------

### 🟢 System Status: Logic Confirmed

You have correctly identified the potential gap, and your intuition is spot on: **The Module itself must provide the definition of what it needs.**

If the Orchestrator or the Frontend has to "guess" or "hardcode" what a module needs, we violate the **Atomic Composition** rule. We would be coupling the "Brain" to the specific implementation of a "Tool."

**The Solution: The `module.json` is the Iron Contract.**

We do not need a separate system. We simply need to enforce a stricter schema in the `module.json` file we defined earlier. This file acts as the **Interface Definition Language (IDL)** for your system.

Here is the operational workflow to ensure **Zero Conflict** between your independent Assets and independent Modules.

---

### 1. The Contract (Updated `module.json`)

We must expand the `inputs` section of `module.json` to be very specific. It must distinguish between an **ASSET** (a file reference from the Asset Service) and a **VALUE** (a raw number or string configuration).

**Example: A "Face Detection" Module Contract**

```json
{
  "name": "face-detect-v1",
  "inputs": [
    {
      "key": "source_video",
      "label": "Input Video File",
      "contract_type": "ASSET",
      "constraints": {
        "media_types": ["video/mp4", "video/mkv"] 
      }
    },
    {
      "key": "confidence_threshold",
      "label": "Detection Confidence",
      "contract_type": "VALUE", 
      "default": 0.5,
      "constraints": {
        "dtype": "float",
        "min": 0.1,
        "max": 1.0
      }
    }
  ],
  "outputs": [
    {
      "key": "faces_archive",
      "label": "Zipped Face Images",
      "contract_type": "ASSET",
      "media_type": "application/zip"
    }
  ]
}

```

### 2. The Implementation: Schema-Driven Frontend

This architecture allows your Frontend to be "dumb." It doesn't know what "Face Detection" is. It just renders a form based on the JSON above.

1. **User Selects Module:** Frontend calls `GET /api/registry/modules/face-detect-v1`.
2. **Frontend Reads `inputs`:**
* It sees `source_video` is type `ASSET` with constraint `video/mp4`.
* **Action:** It opens an "Asset Selector" modal that *only* queries the Asset Service for `status: AVAILABLE` AND `media_type: video/mp4`.
* It sees `confidence_threshold` is type `VALUE` (float).
* **Action:** It renders a Slider or Number Input.


3. **User Submits:** The payload is sent to the Orchestrator.

### 3. The Safeguard: Orchestrator Validation

To answer your fear: *"Are you sure there will be no conflict?"*
**Yes.** Because the Orchestrator performs a **"Pre-Flight Check"** before the task ever enters the queue.

**The Validation Logic (in Orchestrator):**

```python
def validate_task_request(module_def, user_inputs):
    for required_input in module_def['inputs']:
        key = required_input['key']
        user_provided = user_inputs.get(key)

        # 1. Missing Input Check
        if not user_provided:
            raise Error(f"Missing required input: {key}")

        # 2. Asset Type Check
        if required_input['contract_type'] == 'ASSET':
            asset = asset_service.get_metadata(user_provided)
            
            # Does the asset exist?
            if not asset:
                raise Error("Asset ID not found")
            
            # Is the asset the wrong type? (e.g., Audio instead of Video)
            allowed = required_input['constraints']['media_types']
            if asset.media_type not in allowed:
                raise Error(f"Input {key} requires {allowed}, but got {asset.media_type}")

```

### 4. The Execution Flow (Binding Data)

Once validated, the Orchestrator creates the **Task Record**. When the worker picks it up:

1. It reads the Task Record.
2. It asks the Asset Service: "Give me the file paths for these Asset IDs."
3. It asks the Asset Service: "Create temporary files for these Config Values."
4. It generates the `input_manifest.json` pointing to those paths.
5. It runs the module.


-----------------------------------------------------

Explain the update that needs to be made to the Module registry and why it needs to be made

-------------------------------------------------


To maintain the **Atomic Composition** of the system, we must update the **Module Registry** to include a strict **Contract Definition** within each module's metadata (`module.json`).

### The "Why": Solving the Coupling Problem

Currently, the Registry knows how to *install* a module, but it doesn't know how to *talk* to it. If the Registry (or the UI) doesn't know what specific inputs a "Face Tracker" needs vs. a "Transcriber," the system becomes a "Black Box."

Without this update, you would be forced to hardcode logic for every new module into the Orchestrator, creating a **Monolithic Dependency**. By moving the requirement definitions into the module itself, the Orchestrator remains "dumb" and generic, while the Module remains self-describing and independent.

---

### The "What": The Three Critical Updates

#### 1. Input/Output Typing (The Guardrail)

The `module.json` must be updated to define the exact **Data Contract**. We distinguish between `ASSET` (files handled by the Asset Service) and `VALUE` (simple parameters like strings or floats).

**Why:** This allows the UI to automatically generate the correct form (e.g., a file uploader for a video, but a slider for "Volume"). It also allows the Orchestrator to reject a task *before* it runs if the user tries to feed a `.txt` file into a video processing module.

#### 2. Resource Requirements (The Scheduler)

We must add a `resources` section (e.g., `requires_gpu: true`, `min_ram_gb: 8`).

**Why:** Since you are running "heavy duty" ML models, the Registry needs to signal to the Orchestrator whether a module can run on the current hardware. This prevents the system from crashing due to Out-Of-Memory (OOM) errors when multiple heavy modules are queued.

#### 3. Standardized CLI Arguments

We need to enforce how the Registry's `runner.py` executes the `main.py` of a module.

**Why:** In your current setup, the Registry uses `subprocess`. To stay atomic, we must standardize the interface. The Registry should always pass exactly one argument: `--manifest path/to/input_data.json`. This JSON file is the "envelope" containing all the paths and values the module needs.

---

### Comparison: Before vs. After

| Feature | Old Registry (Current) | Updated Atomic Registry |
| --- | --- | --- |
| **Knowledge** | Knows the module exists. | Knows exactly what data types the module requires. |
| **Validation** | Fails only when the code crashes. | Fails early if the input data doesn't match the contract. |
| **UI Support** | Manual UI coding for every module. | Dynamic UI generation based on `module.json`. |
| **Hardware** | Blindly runs tasks. | Respects GPU/RAM constraints of the module. |


----------------------------------------------------


please can we also make sure that the contract is saved to db so on creation of tasks we can use the inputs to add assets of the required type - we don't add videos or such - we just assign assets - 

the upload and all that is under asset management - all tasks use as input is asset allocation (even pending assets are acceptable)

----------------------------------------------------



### 🟢 Atomic Rule Enforcement: The Contract as Data

Your request is perfectly aligned with the **Atomic Composition** philosophy. By saving the contract to the database, you turn the "Module Definition" into a **Schema for Task Creation**.

The Orchestrator will not "guess" how to build a task; it will read the **Module Contract** from the DB and enforce it like a blueprint.

---

### 1. Updated Module Registry Logic

When your `RegistryOrchestrator` scans a module, it will now ingest the `inputs` and `outputs` arrays from `module.json` and store them in the `modules` collection in MongoDB.

**Why this is vital:**
The Frontend can now call `GET /api/modules/face-tracker` and receive a JSON list of required fields. It doesn't need to know the code; it just needs the **Contract**.

---

### 2. The Task Creation Logic (Asset Allocation Only)

You are absolutely correct: **Task creation is purely an exercise in "Asset Mapping."**

When you create a task, you are not uploading files; you are providing a map. The Orchestrator validates this map against the stored Contract.

**Example Task Creation Payload:**

```json
{
  "module_id": "face-tracker-v1",
  "input_mapping": {
    "source_video": "asset_abc_123",  // ID of an EXISTING asset (AVAILABLE)
    "config_json": "asset_xyz_789"    // ID of a PENDING asset (Output of a previous task)
  }
}

```

---

### 3. Comprehensive Blueprint: Asset Service & Registry Update

I will now generate the finalized technical blueprint for the **Asset Service** and the **Registry Update** to handle these contracts.

#### **I. Data Models (Updated)**

**Collection: `modules**`

* Stores the `inputs` and `outputs` schema.
* This is the "Blueprint" the UI uses to show what assets are needed.

**Collection: `assets**`

* **Status:** `PENDING`, `AVAILABLE`, `FAILED`.
* **Type:** `FILE` or `VALUE`.
* **Standardized:** All inputs to a task *must* be an Asset ID. Even a small config string is an `Asset` of type `VALUE`.

#### **II. The Component Interface (The Python Logic)**

We will implement the `AssetManager` to handle this "Allocation-Only" philosophy.

```python
## src/services/asset_service/manager.py

class AssetManager:
    def create_asset_promise(self, label, task_id, media_type):
        """Creates a PENDING asset. Used when a task is queued but not run."""
        
    def fulfill_promise(self, asset_id, storage_path):
        """Updates PENDING to AVAILABLE once the task actually finishes."""

    def resolve_to_path(self, asset_id):
        """
        The "Contract Resolver":
        - If FILE: Returns the real path.
        - If VALUE: Writes value to a temp file, returns that path.
        """

```

---

### 4. Feasibility Check: The "Dependency Chain"

By allowing `PENDING` assets as inputs, you have enabled **Asynchronous Pipelines**.

* **Risk:** A user deletes a parent task while a child task is waiting for its `PENDING` asset.
* **Solution:** The Asset Service must implement **Reference Counting**. You cannot delete an asset if it is "Mapped" to a pending task.

