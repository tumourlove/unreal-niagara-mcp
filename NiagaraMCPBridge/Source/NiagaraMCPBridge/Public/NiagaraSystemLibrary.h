// Copyright NiagaraMCP. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NiagaraSystemLibrary.generated.h"

class UNiagaraSystem;
struct FNiagaraEmitterHandle;

/**
 * Blueprint-callable wrappers for UNiagaraSystem editing operations.
 * All functions load the system from an asset path, perform the operation inside
 * an editor transaction, and return results as JSON strings or booleans.
 */
UCLASS()
class NIAGARAMCPBRIDGE_API UNiagaraMCPSystemLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	// ── Emitter Management ──────────────────────────────────────────────

	/** Add an emitter to a system. Returns the new emitter handle GUID as a string, or empty on failure. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static FString AddEmitter(const FString& SystemPath, const FString& EmitterAssetPath, const FString& EmitterName);

	/** Remove an emitter from a system by handle ID (GUID string) or name. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static bool RemoveEmitter(const FString& SystemPath, const FString& EmitterHandleId);

	/** Duplicate an emitter within a system. Returns the new handle GUID. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static FString DuplicateEmitter(const FString& SystemPath, const FString& SourceHandleId, const FString& NewName);

	/** Enable or disable an emitter. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static bool SetEmitterEnabled(const FString& SystemPath, const FString& EmitterHandleId, bool bEnabled);

	/** Reorder emitters. OrderedHandleIds is a comma-separated list of GUID strings or names. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static bool ReorderEmitters(const FString& SystemPath, const TArray<FString>& OrderedHandleIds);

	/** Set a property on the versioned emitter data by name, with value as JSON. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static bool SetEmitterProperty(const FString& SystemPath, const FString& EmitterHandleId, const FString& PropertyName, const FString& ValueJson);

	// ── System Operations ───────────────────────────────────────────────

	/** Request recompilation of a Niagara system. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static bool RequestCompile(const FString& SystemPath);

	/** Create a new Niagara system. Returns the created asset path, or empty on failure. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|System")
	static FString CreateNiagaraSystem(const FString& SavePath, const FString& TemplatePath);

	// ── Helpers (not exposed to BP) ─────────────────────────────────────

	/** Load a UNiagaraSystem from an asset path. */
	static UNiagaraSystem* LoadSystem(const FString& SystemPath);

	/** Find an emitter handle by GUID string or by name. Returns index or INDEX_NONE. */
	static int32 FindEmitterHandleIndex(UNiagaraSystem* System, const FString& HandleIdOrName);
};
