// Copyright NiagaraMCP. All Rights Reserved.

#include "NiagaraDILibrary.h"

#include "NiagaraDataInterface.h"
#include "NiagaraTypes.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonWriter.h"
#include "Serialization/JsonSerializer.h"

DEFINE_LOG_CATEGORY_STATIC(LogNiagaraMCPDI, Log, All);

// ─────────────────────────────────────────────────────────────────────────────
// GetDataInterfaceFunctions
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPDILibrary::GetDataInterfaceFunctions(const FString& DIClassName)
{
	// Resolve the DI class name
	FString ClassName = DIClassName;

	// Normalize: ensure U prefix and DataInterface suffix
	if (!ClassName.StartsWith(TEXT("U")))
	{
		ClassName = TEXT("U") + ClassName;
	}
	if (!ClassName.Contains(TEXT("DataInterface")))
	{
		ClassName = TEXT("UNiagara") + DIClassName + TEXT("DataInterface");
	}

	// Try multiple name variations
	UClass* DIClass = FindFirstObject<UClass>(*ClassName, EFindFirstObjectOptions::NativeFirst);
	if (!DIClass)
	{
		// Try without U prefix
		DIClass = FindFirstObject<UClass>(*ClassName.Mid(1), EFindFirstObjectOptions::NativeFirst);
	}
	if (!DIClass)
	{
		// Try the raw name as given
		DIClass = FindFirstObject<UClass>(*DIClassName, EFindFirstObjectOptions::NativeFirst);
	}
	if (!DIClass)
	{
		// Try with UNiagara prefix
		FString NiagaraPrefixed = TEXT("UNiagara") + DIClassName;
		DIClass = FindFirstObject<UClass>(*NiagaraPrefixed, EFindFirstObjectOptions::NativeFirst);
		if (!DIClass)
		{
			DIClass = FindFirstObject<UClass>(*NiagaraPrefixed.Mid(1), EFindFirstObjectOptions::NativeFirst);
		}
	}

	if (!DIClass || !DIClass->IsChildOf(UNiagaraDataInterface::StaticClass()))
	{
		UE_LOG(LogNiagaraMCPDI, Error, TEXT("GetDataInterfaceFunctions: could not find DI class '%s'"), *DIClassName);
		return FString();
	}

	// Create a temporary instance to query function signatures
	UNiagaraDataInterface* TempDI = NewObject<UNiagaraDataInterface>(GetTransientPackage(), DIClass);
	if (!TempDI)
	{
		UE_LOG(LogNiagaraMCPDI, Error, TEXT("GetDataInterfaceFunctions: failed to create temp DI instance"));
		return FString();
	}

	// Get function signatures
	TArray<FNiagaraFunctionSignature> Signatures;
	TempDI->GetFunctions(Signatures);

	// Serialize to JSON
	TArray<TSharedPtr<FJsonValue>> JsonArray;
	for (const FNiagaraFunctionSignature& Sig : Signatures)
	{
		TSharedRef<FJsonObject> SigObj = MakeShared<FJsonObject>();
		SigObj->SetStringField(TEXT("name"), Sig.Name.ToString());

		// Inputs
		TArray<TSharedPtr<FJsonValue>> InputsArray;
		for (const FNiagaraVariable& Input : Sig.Inputs)
		{
			TSharedRef<FJsonObject> InputObj = MakeShared<FJsonObject>();
			InputObj->SetStringField(TEXT("name"), Input.GetName().ToString());
			InputObj->SetStringField(TEXT("type"), Input.GetType().GetName());
			InputsArray.Add(MakeShared<FJsonValueObject>(InputObj));
		}
		SigObj->SetArrayField(TEXT("inputs"), InputsArray);

		// Outputs
		TArray<TSharedPtr<FJsonValue>> OutputsArray;
		for (const FNiagaraVariableBase& Output : Sig.Outputs)
		{
			TSharedRef<FJsonObject> OutputObj = MakeShared<FJsonObject>();
			OutputObj->SetStringField(TEXT("name"), Output.GetName().ToString());
			OutputObj->SetStringField(TEXT("type"), Output.GetType().GetName());
			OutputsArray.Add(MakeShared<FJsonValueObject>(OutputObj));
		}
		SigObj->SetArrayField(TEXT("outputs"), OutputsArray);

		// Additional metadata
		SigObj->SetBoolField(TEXT("requires_exec_pin"), Sig.bRequiresExecPin);
		SigObj->SetBoolField(TEXT("member_function"), Sig.bMemberFunction);
		SigObj->SetBoolField(TEXT("requires_context"), Sig.bRequiresContext);
		SigObj->SetBoolField(TEXT("supports_gpu"), Sig.bSupportsGPU);
		SigObj->SetBoolField(TEXT("supports_cpu"), Sig.bSupportsCPU);

		FText SigDescription = Sig.GetDescription();
		if (!SigDescription.IsEmpty())
		{
			SigObj->SetStringField(TEXT("description"), SigDescription.ToString());
		}

		JsonArray.Add(MakeShared<FJsonValueObject>(SigObj));
	}

	FString Result;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
	FJsonSerializer::Serialize(JsonArray, Writer);

	UE_LOG(LogNiagaraMCPDI, Log, TEXT("Found %d functions for DI class '%s'"), Signatures.Num(), *DIClassName);
	return Result;
}
