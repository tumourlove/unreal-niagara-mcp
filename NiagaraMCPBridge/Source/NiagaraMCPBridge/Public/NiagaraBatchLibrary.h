// Copyright NiagaraMCP. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NiagaraBatchLibrary.generated.h"

/**
 * Blueprint-callable batch operations for Niagara systems.
 * Wraps multiple atomic operations into single transactions for efficiency.
 */
UCLASS()
class NIAGARAMCPBRIDGE_API UNiagaraMCPBatchLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	/**
	 * Execute a batch of operations on a system within a single undo transaction.
	 * OperationsJson is a JSON array of operation objects.
	 * Returns JSON with results array and overall success status.
	 *
	 * Supported operations:
	 *   {"op": "add_emitter", "emitter_asset": "/path", "name": "Name"}
	 *   {"op": "remove_emitter", "emitter": "HandleIdOrName"}
	 *   {"op": "add_module", "emitter": "Name", "stage": "particle_spawn", "module": "/path", "index": 0}
	 *   {"op": "remove_module", "emitter": "Name", "module_guid": "GUID"}
	 *   {"op": "set_module_input", "emitter": "Name", "module_name": "ModuleName", "input": "InputName", "value": ...}
	 *   {"op": "set_emitter_property", "emitter": "Name", "property": "PropName", "value": ...}
	 *   {"op": "add_renderer", "emitter": "Name", "class": "sprite"}
	 *   {"op": "remove_renderer", "emitter": "Name", "renderer_index": 0}
	 *   {"op": "set_renderer_material", "emitter": "Name", "renderer_index": 0, "material": "/path"}
	 *   {"op": "set_renderer_property", "emitter": "Name", "renderer_index": 0, "property": "Name", "value": ...}
	 *   {"op": "add_user_param", "name": "ParamName", "type": "float", "default": 1.0}
	 *   {"op": "set_module_binding", "emitter": "Name", "module_name": "ModuleName", "input": "InputName", "binding": "Particles.Velocity"}
	 */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Batch")
	static FString BatchExecute(const FString& SystemPath, const FString& OperationsJson);

	/**
	 * Create a complete Niagara system from a declarative specification.
	 * SpecJson defines the system structure including emitters, modules, renderers, and parameters.
	 *
	 * Spec format:
	 * {
	 *   "save_path": "/Game/VFX/MySystem",
	 *   "template": "/path/to/template" (optional),
	 *   "emitters": [
	 *     {
	 *       "asset": "/path/to/emitter",
	 *       "name": "Sparks",
	 *       "properties": {"sim_target": "GPU", "local_space": false},
	 *       "modules": [
	 *         {"stage": "particle_spawn", "script": "/path", "inputs": {"Lifetime": 2.0}},
	 *       ],
	 *       "renderers": [
	 *         {"class": "sprite", "material": "/path/to/material"}
	 *       ]
	 *     }
	 *   ],
	 *   "user_parameters": [
	 *     {"name": "SpawnRate", "type": "float", "default": 100.0}
	 *   ]
	 * }
	 *
	 * Returns JSON with the created system path and detailed results.
	 */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Batch")
	static FString CreateSystemFromSpec(const FString& SpecJson);
};
