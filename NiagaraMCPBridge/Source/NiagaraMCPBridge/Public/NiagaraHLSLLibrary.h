// Copyright NiagaraMCP. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NiagaraHLSLLibrary.generated.h"

/**
 * Blueprint-callable wrapper for extracting compiled GPU HLSL from Niagara emitters.
 */
UCLASS()
class NIAGARAMCPBRIDGE_API UNiagaraMCPHLSLLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	/** Get the compiled GPU HLSL source for an emitter's GPU compute script. Returns the HLSL string. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|HLSL")
	static FString GetCompiledGPUHLSL(const FString& SystemPath, const FString& EmitterHandleId);
};
