// Copyright NiagaraMCP. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "NiagaraDILibrary.generated.h"

/**
 * Blueprint-callable wrapper for inspecting Niagara Data Interface function signatures.
 */
UCLASS()
class NIAGARAMCPBRIDGE_API UNiagaraMCPDILibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:

	/** Get all function signatures exposed by a data interface class. Returns JSON array. */
	UFUNCTION(BlueprintCallable, Category = "NiagaraMCP|DI")
	static FString GetDataInterfaceFunctions(const FString& DIClassName);
};
