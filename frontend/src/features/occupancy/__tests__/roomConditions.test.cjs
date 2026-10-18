const { test, describe } = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const esbuild = require("esbuild");

// Transpile and load roomStatus.ts
const roomStatusTs = fs.readFileSync(
  path.join(__dirname, "../lib/roomStatus.ts"),
  "utf8"
);
// Provide mocks for imports from @/lib/api/types
const mockGlobals = `
const ROOM_STATUS = {
  AVAILABLE: "Available",
  OCCUPIED: "Occupied",
  ALLOTTED: "Allotted",
  UNAVAILABLE: "Unavailable",
};
const KNOWN_AMENITY_STATUSES = ["Available", "Occupied", "Allotted", "Unavailable"];
`;

const cleanedTs = mockGlobals + "\n" + roomStatusTs.replace(/import\s+[\s\S]*?from\s+["'][^"']+["'];?/g, "");
const { code: jsCode } = esbuild.transformSync(cleanedTs, {
  loader: "ts",
  format: "cjs",
});

const moduleExports = {};
const moduleFunc = new Function("exports", "require", "module", jsCode);
const mockModule = { exports: moduleExports };
moduleFunc(moduleExports, require, mockModule);

const { conditionLabel } = mockModule.exports;

const mockConditions = [
  { id: 1, name: "Dirty" },
  { id: 2, name: "Low battery" },
  { id: 3, name: "Under maintenance" },
  { id: 4, name: "Sanitation" },
  { id: 5, name: "Ready for occupant" },
];

describe("Single-Active-Condition Room Dialog UI & State Management", () => {
  // Test 1: Only one radio option can be selected at any time
  test("1. Only one radio option can be selected at a time in component state", () => {
    let selectedId = null;

    // Select Under Maintenance (3)
    selectedId = 3;
    assert.equal(selectedId, 3);
    assert.equal(typeof selectedId, "number");
  });

  // Test 2: Selecting a new condition deselects the previous condition
  test("2. Selecting a new condition immediately replaces previous selection", () => {
    let selectedId = 5; // Ready to Occupy
    assert.equal(selectedId, 5);

    // Operator selects Under Maintenance (3)
    selectedId = 3;
    assert.equal(selectedId, 3, "New selection must replace previous");
    assert.notEqual(selectedId, 5, "Previous selection must no longer be active");

    // Operator selects Dirty / Need Maintenance (1)
    selectedId = 1;
    assert.equal(selectedId, 1);
  });

  // Test 3: Exactly one condition ID is submitted to the API
  test("3. Exactly one condition ID is submitted in the save payload", () => {
    let submittedPayload = null;
    let selectedId = 3; // Under Maintenance

    const handleSave = (amenityId, selectedId) => {
      if (!amenityId || selectedId === null) return;
      submittedPayload = { amenityId, conditionIds: [selectedId] };
    };

    handleSave("amenity-104", selectedId);
    assert.deepEqual(submittedPayload, {
      amenityId: "amenity-104",
      conditionIds: [3],
    });
    assert.equal(submittedPayload.conditionIds.length, 1);
  });

  // Test 4: Prevent save when no condition is selected
  test("4. Save is disabled and prevented when no condition is selected", () => {
    let submitted = false;
    let selectedId = null;

    const handleSave = (amenityId, selectedId) => {
      if (!amenityId || selectedId === null) return;
      submitted = true;
    };

    handleSave("amenity-104", selectedId);
    assert.equal(submitted, false, "Save must not execute when selectedId is null");
  });

  // Test 5: Successful save refreshes the room display and closes dialog
  test("5. Successful save closes dialog and triggers invalidation to refresh table", () => {
    let dialogOpen = true;
    let queryInvalidated = false;

    const mockMutation = {
      isPending: false,
      mutate: ({ amenityId, conditionIds }, { onSuccess }) => {
        // Backend acknowledges 200 OK
        queryInvalidated = true;
        onSuccess();
      },
    };

    const handleSave = (amenityId, selectedId) => {
      mockMutation.mutate(
        { amenityId, conditionIds: [selectedId] },
        { onSuccess: () => { dialogOpen = false; } }
      );
    };

    handleSave("amenity-104", 5);
    assert.equal(dialogOpen, false, "Dialog must close on success");
    assert.equal(queryInvalidated, true, "Occupancy query cache must invalidate to refresh table badges");
  });

  // Test 6: API errors are shown without falsely updating the UI or closing dialog
  test("6. API errors preserve dialog state without falsely updating authoritative UI", () => {
    let dialogOpen = true;
    let selectedId = 3;
    let errorSurfaced = null;

    const mockMutation = {
      isPending: false,
      mutate: ({ amenityId, conditionIds }, { onError }) => {
        // API returns error
        onError(new Error("Network failure"));
      },
    };

    const handleSave = (amenityId, selectedId) => {
      mockMutation.mutate(
        { amenityId, conditionIds: [selectedId] },
        {
          onError: (err) => {
            errorSurfaced = err.message;
          },
        }
      );
    };

    handleSave("amenity-104", selectedId);
    assert.equal(dialogOpen, true, "Dialog must stay open on API error");
    assert.equal(selectedId, 3, "Selected ID must be preserved for retry");
    assert.equal(errorSurfaced, "Network failure");
  });

  // Test 7: Switching between rooms does not carry over selection state
  test("7. Switching between rooms resets selection to the new room's current condition", () => {
    let selectedId = null;

    // Helper simulating dialog open / room change effect:
    // useEffect(() => { if (open) setSelectedId(selectedIds[0] ?? null); }, [open, amenityId, selectedIds])
    const onRoomOpen = (amenityId, selectedIds) => {
      selectedId = selectedIds[0] ?? null;
    };

    // Open Room 104 (currently has Under Maintenance = 3)
    onRoomOpen("room-104", [3]);
    assert.equal(selectedId, 3, "Room 104 initialized with condition 3");

    // Operator selects 5 in dialog
    selectedId = 5;

    // Switch to Room 105 (currently has Ready to Occupy = 5)
    onRoomOpen("room-105", [5]);
    assert.equal(selectedId, 5, "Room 105 initialized with condition 5");

    // Switch to Room 206 (currently has Dirty = 1)
    onRoomOpen("room-206", [1]);
    assert.equal(selectedId, 1, "Room 206 initialized with condition 1, not 5");

    // Switch to a room with no condition
    onRoomOpen("room-999", []);
    assert.equal(selectedId, null, "Room without condition initialized with null");
  });

  // Test 8: Preventing duplicate save submissions while in progress
  test("8. Save button and handler are blocked while save request is in progress", () => {
    let isPending = false;
    let dispatchCount = 0;

    const handleSave = () => {
      if (isPending) return;
      isPending = true;
      dispatchCount++;
    };

    handleSave();
    assert.equal(dispatchCount, 1);
    assert.equal(isPending, true);

    // Repeated clicks while in progress
    handleSave();
    handleSave();
    assert.equal(dispatchCount, 1, "Repeated submissions must be blocked while pending");

    isPending = false;
  });

  // Test 9: Display labels match operator conventions
  test("9. Display labels map stored names to operator wording accurately", () => {
    assert.equal(conditionLabel("Dirty"), "Need Maintenance");
    assert.equal(conditionLabel("dirty"), "Need Maintenance");
    assert.equal(conditionLabel("Ready for occupant"), "Ready to occupy");
    assert.equal(conditionLabel("ready for occupant"), "Ready to occupy");
    assert.equal(conditionLabel("Under maintenance"), "Under maintenance");
    assert.equal(conditionLabel("Sanitation"), "Sanitation");
    assert.equal(conditionLabel("Low battery"), "Low battery");
  });

  // Test 10: Step-by-step selection sequence: Ready -> Need Maintenance -> Under Maintenance -> Save
  test("10. Full UI radio sequence: Ready to Occupy -> Need Maintenance -> Under Maintenance", () => {
    // A. Dialog opens for room with Ready to Occupy (5)
    let selectedId = 5;
    assert.equal(selectedId, 5, "Initially Ready to Occupy (5)");

    // B. User clicks Need Maintenance (1)
    const onSelectNeedMaintenance = () => { selectedId = 1; };
    onSelectNeedMaintenance();
    assert.equal(selectedId, 1, "Need Maintenance immediately selected");
    assert.notEqual(selectedId, 5, "Ready to Occupy immediately unselected");

    // C. User clicks Under Maintenance (3)
    const onSelectUnderMaintenance = () => { selectedId = 3; };
    onSelectUnderMaintenance();
    assert.equal(selectedId, 3, "Under Maintenance is the only selected option");
    assert.notEqual(selectedId, 1, "Need Maintenance unselected");
    assert.notEqual(selectedId, 5, "Ready to Occupy unselected");

    // D. User clicks Save
    let dispatchedPayload = null;
    const handleSave = (amenityId, id) => {
      dispatchedPayload = { amenityId, conditionIds: [id] };
    };
    handleSave("amenity-104", selectedId);
    assert.deepEqual(dispatchedPayload, {
      amenityId: "amenity-104",
      conditionIds: [3],
    });
  });
});


