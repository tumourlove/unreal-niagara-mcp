// Copyright NiagaraMCP. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NiagaraCommon.h"
#include "NiagaraModuleLibrary.generated.h"

class UNiagaraSystem;
class UNiagaraNodeOutput;
class UNiagaraNodeFunctionCall;
class UNiagaraScript;
class UNiagaraGraph;

/**
 * Blueprint-callable wrappers for Niagara module stack operations.
 * Wraps FNiagaraStackGraphUtilities and NiagaraEditor APIs.
 */
UCLASS()
class NIAGARAMCPBRIDGE_API UNiagaraMCPModuleLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	// ── Module Stack Queries ────────────────────────────────────────────

	/** Get ordered modules for a script stage. Returns JSON array of module info. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static FString GetOrderedModules(const FString& SystemPath, const FString& EmitterHandleId, const FString& ScriptUsage);

	/** Get inputs for a specific module. Returns JSON array of input info. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static FString GetModuleInputs(const FString& SystemPath, const FString& EmitterHandleId, const FString& ModuleNodeGuid);

	/** Get the node graph of a module script asset. Returns JSON. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static FString GetModuleGraph(const FString& ModuleScriptPath);

	// ── Module Stack Mutations ──────────────────────────────────────────

	/** Add a module to a script stage. Returns new node GUID string. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static FString AddModule(const FString& SystemPath, const FString& EmitterHandleId,
		const FString& ScriptUsage, const FString& ModuleScriptPath, int32 Index);

	/** Remove a module from the stack by node GUID. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static bool RemoveModule(const FString& SystemPath, const FString& EmitterHandleId, const FString& ModuleNodeGuid);

	/** Move a module to a new index within its stage. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static bool MoveModule(const FString& SystemPath, const FString& EmitterHandleId,
		const FString& ModuleNodeGuid, int32 NewIndex);

	/** Enable or disable a module. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static bool SetModuleEnabled(const FString& SystemPath, const FString& EmitterHandleId,
		const FString& ModuleNodeGuid, bool bEnabled);

	/** Set a static value on a module input. ValueJson contains the typed value. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static bool SetModuleInputValue(const FString& SystemPath, const FString& EmitterHandleId,
		const FString& ModuleNodeGuid, const FString& InputName, const FString& ValueJson);

	/** Bind a module input to a parameter path (e.g., "Particles.Velocity"). */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static bool SetModuleInputBinding(const FString& SystemPath, const FString& EmitterHandleId,
		const FString& ModuleNodeGuid, const FString& InputName, const FString& BindingPath);

	/** Set a data interface on a module input. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static bool SetModuleInputDI(const FString& SystemPath, const FString& EmitterHandleId,
		const FString& ModuleNodeGuid, const FString& InputName,
		const FString& DIClass, const FString& DIConfigJson);

	// ── Module Creation ─────────────────────────────────────────────────

	/** Create a new module script from HLSL code. Returns asset path. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static FString CreateModuleFromHLSL(const FString& SavePath, const FString& HLSLCode,
		const FString& InputsJson, const FString& OutputsJson);

	/** Create a new function script from HLSL code. Returns asset path. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Module")
	static FString CreateFunctionFromHLSL(const FString& SavePath, const FString& HLSLCode,
		const FString& InputsJson, const FString& OutputsJson);

	// ── Helpers (not exposed to BP) ─────────────────────────────────────

	/** Convert a script usage string to the enum. */
	static ENiagaraScriptUsage ResolveScriptUsage(const FString& UsageString);

	/** Find the output node for a given script usage in a system/emitter. */
	static UNiagaraNodeOutput* FindOutputNode(UNiagaraSystem* System, const FString& EmitterHandleId, ENiagaraScriptUsage Usage);

	/** Find a module node by its GUID within a system/emitter. */
	static UNiagaraNodeFunctionCall* FindModuleNode(UNiagaraSystem* System, const FString& EmitterHandleId,
		const FString& NodeGuidStr, ENiagaraScriptUsage* OutUsage = nullptr);

	/** Get the NiagaraGraph for a given emitter script usage. */
	static UNiagaraGraph* GetGraphForUsage(UNiagaraSystem* System, const FString& EmitterHandleId, ENiagaraScriptUsage Usage);
};
