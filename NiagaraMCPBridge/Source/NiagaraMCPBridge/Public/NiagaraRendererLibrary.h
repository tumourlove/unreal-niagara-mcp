// Copyright NiagaraMCP. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NiagaraRendererLibrary.generated.h"

class UNiagaraSystem;
class UNiagaraRendererProperties;
struct FVersionedNiagaraEmitterData;

/**
 * Blueprint-callable wrappers for Niagara renderer operations.
 * Handles adding/removing renderers, setting materials, properties, and bindings.
 */
UCLASS()
class NIAGARAMCPBRIDGE_API UNiagaraMCPRendererLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	// ── Renderer Mutations ─────────────────────────────────────────────

	/** Add a renderer to an emitter. Returns the new renderer index, or -1 on failure. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Renderer")
	static int32 AddRenderer(const FString& SystemPath, const FString& EmitterHandleId, const FString& RendererClass);

	/** Remove a renderer from an emitter by index. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Renderer")
	static bool RemoveRenderer(const FString& SystemPath, const FString& EmitterHandleId, int32 RendererIndex);

	/** Set the material on a renderer. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Renderer")
	static bool SetRendererMaterial(const FString& SystemPath, const FString& EmitterHandleId,
		int32 RendererIndex, const FString& MaterialPath);

	/** Set a property on a renderer by name, with value as JSON. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Renderer")
	static bool SetRendererProperty(const FString& SystemPath, const FString& EmitterHandleId,
		int32 RendererIndex, const FString& PropertyName, const FString& ValueJson);

	/** Get all bindings on a renderer. Returns JSON. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Renderer")
	static FString GetRendererBindings(const FString& SystemPath, const FString& EmitterHandleId, int32 RendererIndex);

	/** Set a binding on a renderer to an attribute path. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|Renderer")
	static bool SetRendererBinding(const FString& SystemPath, const FString& EmitterHandleId,
		int32 RendererIndex, const FString& BindingName, const FString& AttributePath);

	// ── Helpers (not exposed to BP) ─────────────────────────────────────

	/** Resolve a renderer class string to UClass*. */
	static UClass* ResolveRendererClass(const FString& RendererClass);

	/** Get versioned emitter data and the renderer at the given index. */
	static UNiagaraRendererProperties* GetRenderer(UNiagaraSystem* System, const FString& EmitterHandleId,
		int32 RendererIndex, FVersionedNiagaraEmitterData** OutEmitterData = nullptr);
};
