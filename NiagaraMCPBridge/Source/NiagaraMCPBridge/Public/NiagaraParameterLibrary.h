// Copyright NiagaraMCP. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NiagaraTypes.h"
#include "NiagaraParameterLibrary.generated.h"

class UNiagaraSystem;
struct FNiagaraVariable;
struct FNiagaraParameterStore;

/**
 * Blueprint-callable wrappers for Niagara parameter store operations.
 * Handles user parameters, system/emitter parameters, type resolution, and value serialization.
 */
UCLASS()
class NIAGARAMCPBRIDGE_API UNiagaraMCPParameterLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	// ── Parameter Queries ───────────────────────────────────────────────

	/** Get all parameters across system and emitter stores. Returns JSON. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static FString GetAllParameters(const FString& SystemPath);

	/** Get user-exposed parameters. Returns JSON array. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static FString GetUserParameters(const FString& SystemPath);

	/** Get the value of a specific parameter. Returns JSON. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static FString GetParameterValue(const FString& SystemPath, const FString& ParamName);

	/** Get type information for a Niagara type name. Returns JSON. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static FString GetParameterType(const FString& TypeName);

	/** Trace a parameter's binding chain from user exposure through emitter stores to module inputs. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static FString TraceParameterBinding(const FString& SystemPath, const FString& ParamName);

	// ── Parameter Mutations ─────────────────────────────────────────────

	/** Add a user parameter to the system's exposed parameter store. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static bool AddUserParameter(const FString& SystemPath, const FString& ParamName,
		const FString& TypeName, const FString& DefaultValueJson);

	/** Remove a user parameter from the system's exposed parameter store. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static bool RemoveUserParameter(const FString& SystemPath, const FString& ParamName);

	/** Set the default value of a parameter. Type is inferred from the parameter's type definition. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static bool SetParameterDefault(const FString& SystemPath, const FString& ParamName, const FString& ValueJson);

	/** Set curve keys on a module input parameter. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Parameter")
	static bool SetCurveValue(const FString& SystemPath, const FString& EmitterHandleId,
		const FString& ModuleName, const FString& InputName, const FString& CurveKeysJson);

	// ── Helpers (not exposed to BP) ─────────────────────────────────────

	/** Resolve a type name string to FNiagaraTypeDefinition. */
	static FNiagaraTypeDefinition ResolveNiagaraType(const FString& TypeName);

	/** Serialize a parameter's value to a JSON string based on its type. */
	static FString SerializeParameterValue(const FNiagaraVariable& Variable, const FNiagaraParameterStore& Store);

	/** Create a properly namespaced user variable. */
	static FNiagaraVariable MakeUserVariable(const FString& ParamName, const FNiagaraTypeDefinition& TypeDef);
};
