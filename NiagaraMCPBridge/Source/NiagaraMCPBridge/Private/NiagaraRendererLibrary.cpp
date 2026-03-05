// Copyright NiagaraMCP. All Rights Reserved.

#include "NiagaraRendererLibrary.h"
#include "NiagaraSystemLibrary.h"

#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraRendererProperties.h"
#include "NiagaraSpriteRendererProperties.h"
#include "NiagaraMeshRendererProperties.h"
#include "NiagaraRibbonRendererProperties.h"
#include "NiagaraLightRendererProperties.h"
#include "NiagaraComponentRendererProperties.h"

#include "Materials/MaterialInterface.h"
#include "Editor.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogNiagaraMCPRenderer, Log, All);

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

static FString RendererJsonToString(const TSharedRef<FJsonObject>& Obj)
{
	FString Result;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
	FJsonSerializer::Serialize(Obj, Writer);
	return Result;
}

static FString RendererJsonArrayToString(const TArray<TSharedPtr<FJsonValue>>& Arr)
{
	FString Result;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
	FJsonSerializer::Serialize(Arr, Writer);
	return Result;
}

UClass* UNiagaraMCPRendererLibrary::ResolveRendererClass(const FString& RendererClass)
{
	FString Lower = RendererClass.ToLower();

	if (Lower == TEXT("sprite") || Lower == TEXT("spriterenderer"))
	{
		return UNiagaraSpriteRendererProperties::StaticClass();
	}
	if (Lower == TEXT("mesh") || Lower == TEXT("meshrenderer"))
	{
		return UNiagaraMeshRendererProperties::StaticClass();
	}
	if (Lower == TEXT("ribbon") || Lower == TEXT("ribbonrenderer"))
	{
		return UNiagaraRibbonRendererProperties::StaticClass();
	}
	if (Lower == TEXT("light") || Lower == TEXT("lightrenderer"))
	{
		return UNiagaraLightRendererProperties::StaticClass();
	}
	if (Lower == TEXT("component") || Lower == TEXT("componentrenderer"))
	{
		return UNiagaraComponentRendererProperties::StaticClass();
	}

	// Try finding by full class name
	FString FullName = RendererClass;
	if (!FullName.StartsWith(TEXT("UNiagara")))
	{
		FullName = TEXT("UNiagara") + FullName;
	}
	if (!FullName.EndsWith(TEXT("Properties")) && !FullName.EndsWith(TEXT("RendererProperties")))
	{
		FullName += TEXT("RendererProperties");
	}

	UClass* FoundClass = FindFirstObject<UClass>(*FullName, EFindFirstObjectOptions::NativeFirst);
	if (!FoundClass)
	{
		// Try without U prefix
		FoundClass = FindFirstObject<UClass>(*FullName.Mid(1), EFindFirstObjectOptions::NativeFirst);
	}

	if (!FoundClass)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("ResolveRendererClass: unknown renderer class '%s'"), *RendererClass);
	}
	return FoundClass;
}

UNiagaraRendererProperties* UNiagaraMCPRendererLibrary::GetRenderer(UNiagaraSystem* System, const FString& EmitterHandleId,
	int32 RendererIndex, FVersionedNiagaraEmitterData** OutEmitterData)
{
	if (!System)
	{
		return nullptr;
	}

	int32 EmitterIdx = UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(System, EmitterHandleId);
	if (EmitterIdx == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("GetRenderer: emitter handle '%s' not found"), *EmitterHandleId);
		return nullptr;
	}

	const FNiagaraEmitterHandle& Handle = System->GetEmitterHandles()[EmitterIdx];
	FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData();
	if (!EmitterData)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("GetRenderer: no emitter data for handle '%s'"), *EmitterHandleId);
		return nullptr;
	}

	if (OutEmitterData)
	{
		*OutEmitterData = EmitterData;
	}

	const TArray<UNiagaraRendererProperties*>& Renderers = EmitterData->GetRenderers();
	if (!Renderers.IsValidIndex(RendererIndex))
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("GetRenderer: renderer index %d out of range (count: %d)"),
			RendererIndex, Renderers.Num());
		return nullptr;
	}

	return Renderers[RendererIndex];
}

// ─────────────────────────────────────────────────────────────────────────────
// AddRenderer
// ─────────────────────────────────────────────────────────────────────────────

int32 UNiagaraMCPRendererLibrary::AddRenderer(const FString& SystemPath, const FString& EmitterHandleId, const FString& RendererClass)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return -1;
	}

	UClass* RendererUClass = ResolveRendererClass(RendererClass);
	if (!RendererUClass)
	{
		return -1;
	}

	int32 EmitterIdx = UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(System, EmitterHandleId);
	if (EmitterIdx == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("AddRenderer: emitter handle '%s' not found"), *EmitterHandleId);
		return -1;
	}

	const FNiagaraEmitterHandle& Handle = System->GetEmitterHandles()[EmitterIdx];
	FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData();
	if (!EmitterData)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("AddRenderer: no emitter data"));
		return -1;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "AddRenderer", "Add Renderer"));
	System->Modify();

	FVersionedNiagaraEmitter EmitterInstance = Handle.GetInstance();
	UNiagaraRendererProperties* NewRenderer = NewObject<UNiagaraRendererProperties>(
		EmitterInstance.Emitter, RendererUClass, NAME_None, RF_Transactional);

	if (!NewRenderer)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("AddRenderer: failed to create renderer instance"));
		GEditor->EndTransaction();
		return -1;
	}

	EmitterInstance.Emitter->AddRenderer(NewRenderer, EmitterInstance.Version);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	int32 NewIndex = EmitterData->GetRenderers().Num() - 1;
	UE_LOG(LogNiagaraMCPRenderer, Log, TEXT("Added %s renderer at index %d to emitter '%s'"),
		*RendererClass, NewIndex, *EmitterHandleId);
	return NewIndex;
}

// ─────────────────────────────────────────────────────────────────────────────
// RemoveRenderer
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPRendererLibrary::RemoveRenderer(const FString& SystemPath, const FString& EmitterHandleId, int32 RendererIndex)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	FVersionedNiagaraEmitterData* EmitterData = nullptr;
	UNiagaraRendererProperties* Renderer = GetRenderer(System, EmitterHandleId, RendererIndex, &EmitterData);
	if (!Renderer || !EmitterData)
	{
		return false;
	}

	int32 EmitterIdx = UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(System, EmitterHandleId);
	const FNiagaraEmitterHandle& Handle = System->GetEmitterHandles()[EmitterIdx];
	FVersionedNiagaraEmitter EmitterInstance = Handle.GetInstance();

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "RemoveRenderer", "Remove Renderer"));
	System->Modify();

	EmitterInstance.Emitter->RemoveRenderer(Renderer, EmitterInstance.Version);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPRenderer, Log, TEXT("Removed renderer at index %d from emitter '%s'"),
		RendererIndex, *EmitterHandleId);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetRendererMaterial
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPRendererLibrary::SetRendererMaterial(const FString& SystemPath, const FString& EmitterHandleId,
	int32 RendererIndex, const FString& MaterialPath)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	UNiagaraRendererProperties* Renderer = GetRenderer(System, EmitterHandleId, RendererIndex);
	if (!Renderer)
	{
		return false;
	}

	UMaterialInterface* Material = LoadObject<UMaterialInterface>(nullptr, *MaterialPath);
	if (!Material)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("SetRendererMaterial: failed to load material '%s'"), *MaterialPath);
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetRendererMat", "Set Renderer Material"));
	System->Modify();
	Renderer->Modify();

	bool bSuccess = false;

	// Handle each renderer type's material property
	if (UNiagaraSpriteRendererProperties* Sprite = Cast<UNiagaraSpriteRendererProperties>(Renderer))
	{
		Sprite->Material = Material;
		bSuccess = true;
	}
	else if (UNiagaraMeshRendererProperties* Mesh = Cast<UNiagaraMeshRendererProperties>(Renderer))
	{
		// Mesh renderer uses OverrideMaterials directly
		Mesh->bOverrideMaterials = true;
		Mesh->OverrideMaterials.SetNum(1);
		Mesh->OverrideMaterials[0].ExplicitMat = Material;
		bSuccess = true;
	}
	else if (UNiagaraRibbonRendererProperties* Ribbon = Cast<UNiagaraRibbonRendererProperties>(Renderer))
	{
		Ribbon->Material = Material;
		bSuccess = true;
	}
	else
	{
		// Try setting via reflection for other renderer types
		FProperty* MatProp = Renderer->GetClass()->FindPropertyByName(TEXT("Material"));
		if (MatProp)
		{
			if (FObjectProperty* ObjProp = CastField<FObjectProperty>(MatProp))
			{
				ObjProp->SetObjectPropertyValue(ObjProp->ContainerPtrToValuePtr<void>(Renderer), Material);
				bSuccess = true;
			}
		}
		else
		{
			UE_LOG(LogNiagaraMCPRenderer, Warning, TEXT("SetRendererMaterial: renderer type '%s' does not have a direct Material property"),
				*Renderer->GetClass()->GetName());
		}
	}

	GEditor->EndTransaction();

	if (bSuccess)
	{
		System->RequestCompile(false);
		UE_LOG(LogNiagaraMCPRenderer, Log, TEXT("Set material '%s' on renderer %d of emitter '%s'"),
			*MaterialPath, RendererIndex, *EmitterHandleId);
	}

	return bSuccess;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetRendererProperty
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPRendererLibrary::SetRendererProperty(const FString& SystemPath, const FString& EmitterHandleId,
	int32 RendererIndex, const FString& PropertyName, const FString& ValueJson)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	UNiagaraRendererProperties* Renderer = GetRenderer(System, EmitterHandleId, RendererIndex);
	if (!Renderer)
	{
		return false;
	}

	// Parse the JSON value
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ValueJson);
	TSharedPtr<FJsonValue> JsonValue;
	if (!FJsonSerializer::Deserialize(Reader, JsonValue) || !JsonValue.IsValid())
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("SetRendererProperty: failed to parse JSON: %s"), *ValueJson);
		return false;
	}

	// Find the property via reflection
	FProperty* Prop = Renderer->GetClass()->FindPropertyByName(FName(*PropertyName));
	if (!Prop)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("SetRendererProperty: property '%s' not found on renderer class '%s'"),
			*PropertyName, *Renderer->GetClass()->GetName());
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetRendererProp", "Set Renderer Property"));
	System->Modify();
	Renderer->Modify();

	void* PropAddr = Prop->ContainerPtrToValuePtr<void>(Renderer);
	bool bSuccess = false;

	if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Prop))
	{
		FloatProp->SetPropertyValue(PropAddr, static_cast<float>(JsonValue->AsNumber()));
		bSuccess = true;
	}
	else if (FDoubleProperty* DoubleProp = CastField<FDoubleProperty>(Prop))
	{
		DoubleProp->SetPropertyValue(PropAddr, JsonValue->AsNumber());
		bSuccess = true;
	}
	else if (FIntProperty* IntProp = CastField<FIntProperty>(Prop))
	{
		IntProp->SetPropertyValue(PropAddr, static_cast<int32>(JsonValue->AsNumber()));
		bSuccess = true;
	}
	else if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Prop))
	{
		BoolProp->SetPropertyValue(PropAddr, JsonValue->AsBool());
		bSuccess = true;
	}
	else if (FStrProperty* StrProp = CastField<FStrProperty>(Prop))
	{
		StrProp->SetPropertyValue(PropAddr, JsonValue->AsString());
		bSuccess = true;
	}
	else if (FEnumProperty* EnumProp = CastField<FEnumProperty>(Prop))
	{
		// Set enum by string name or integer value
		UEnum* Enum = EnumProp->GetEnum();
		if (Enum)
		{
			FString ValStr = JsonValue->AsString();
			int64 EnumVal = Enum->GetValueByNameString(ValStr);
			if (EnumVal == INDEX_NONE)
			{
				EnumVal = static_cast<int64>(JsonValue->AsNumber());
			}
			FNumericProperty* UnderlyingProp = EnumProp->GetUnderlyingProperty();
			if (UnderlyingProp)
			{
				UnderlyingProp->SetIntPropertyValue(PropAddr, EnumVal);
				bSuccess = true;
			}
		}
	}
	else if (FByteProperty* ByteProp = CastField<FByteProperty>(Prop))
	{
		if (ByteProp->Enum)
		{
			FString ValStr = JsonValue->AsString();
			int64 EnumVal = ByteProp->Enum->GetValueByNameString(ValStr);
			if (EnumVal == INDEX_NONE)
			{
				EnumVal = static_cast<int64>(JsonValue->AsNumber());
			}
			ByteProp->SetPropertyValue(PropAddr, static_cast<uint8>(EnumVal));
		}
		else
		{
			ByteProp->SetPropertyValue(PropAddr, static_cast<uint8>(JsonValue->AsNumber()));
		}
		bSuccess = true;
	}
	else if (FObjectProperty* ObjProp = CastField<FObjectProperty>(Prop))
	{
		// Try to load the object from the path
		FString ObjPath = JsonValue->AsString();
		UObject* Obj = LoadObject<UObject>(nullptr, *ObjPath);
		if (Obj)
		{
			ObjProp->SetObjectPropertyValue(PropAddr, Obj);
			bSuccess = true;
		}
		else
		{
			UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("SetRendererProperty: failed to load object '%s'"), *ObjPath);
		}
	}
	else
	{
		// Try import from text as a last resort
		FString ImportText = JsonValue->AsString();
		if (Prop->ImportText_Direct(*ImportText, PropAddr, Renderer, PPF_None))
		{
			bSuccess = true;
		}
		else
		{
			UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("SetRendererProperty: unsupported property type for '%s'"), *PropertyName);
		}
	}

	GEditor->EndTransaction();

	if (bSuccess)
	{
		System->RequestCompile(false);
		UE_LOG(LogNiagaraMCPRenderer, Log, TEXT("Set renderer property '%s' on renderer %d of emitter '%s'"),
			*PropertyName, RendererIndex, *EmitterHandleId);
	}

	return bSuccess;
}

// ─────────────────────────────────────────────────────────────────────────────
// GetRendererBindings
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPRendererLibrary::GetRendererBindings(const FString& SystemPath, const FString& EmitterHandleId, int32 RendererIndex)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	UNiagaraRendererProperties* Renderer = GetRenderer(System, EmitterHandleId, RendererIndex);
	if (!Renderer)
	{
		return FString();
	}

	TArray<TSharedPtr<FJsonValue>> BindingsArray;

	// Iterate over all FNiagaraVariableAttributeBinding properties using reflection
	UClass* RendererClass = Renderer->GetClass();
	for (TFieldIterator<FProperty> It(RendererClass); It; ++It)
	{
		FProperty* Prop = *It;
		if (!Prop)
		{
			continue;
		}

		FStructProperty* StructProp = CastField<FStructProperty>(Prop);
		if (!StructProp)
		{
			continue;
		}

		// Check if this is a binding struct (FNiagaraVariableAttributeBinding or similar)
		FString StructName = StructProp->Struct->GetName();
		if (!StructName.Contains(TEXT("Binding")))
		{
			continue;
		}

		const void* PropAddr = StructProp->ContainerPtrToValuePtr<void>(Renderer);

		TSharedRef<FJsonObject> BindingObj = MakeShared<FJsonObject>();
		BindingObj->SetStringField(TEXT("name"), Prop->GetName());
		BindingObj->SetStringField(TEXT("struct_type"), StructName);

		// Try to export the binding value as text
		FString ExportedText;
		StructProp->ExportTextItem_Direct(ExportedText, PropAddr, nullptr, Renderer, PPF_None);
		BindingObj->SetStringField(TEXT("value"), ExportedText);

		BindingsArray.Add(MakeShared<FJsonValueObject>(BindingObj));
	}

	return RendererJsonArrayToString(BindingsArray);
}

// ─────────────────────────────────────────────────────────────────────────────
// SetRendererBinding
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPRendererLibrary::SetRendererBinding(const FString& SystemPath, const FString& EmitterHandleId,
	int32 RendererIndex, const FString& BindingName, const FString& AttributePath)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	UNiagaraRendererProperties* Renderer = GetRenderer(System, EmitterHandleId, RendererIndex);
	if (!Renderer)
	{
		return false;
	}

	// Find the binding property by name
	UClass* RendererClass = Renderer->GetClass();
	FStructProperty* BindingProp = nullptr;

	for (TFieldIterator<FProperty> It(RendererClass); It; ++It)
	{
		FProperty* Prop = *It;
		if (Prop->GetName() == BindingName)
		{
			BindingProp = CastField<FStructProperty>(Prop);
			break;
		}
	}

	if (!BindingProp)
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("SetRendererBinding: binding property '%s' not found on renderer"),
			*BindingName);
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetRendererBinding", "Set Renderer Binding"));
	System->Modify();
	Renderer->Modify();

	void* PropAddr = BindingProp->ContainerPtrToValuePtr<void>(Renderer);

	// Use ImportText to set the binding value
	// The attribute path format matches Niagara's internal representation
	FString ImportText = FString::Printf(TEXT("(BoundVariable=(Name=\"%s\"))"), *AttributePath);
	bool bSuccess = BindingProp->ImportText_Direct(*ImportText, PropAddr, Renderer, PPF_None) != nullptr;

	if (!bSuccess)
	{
		// Fallback: try direct name assignment for FNiagaraVariableAttributeBinding
		// The binding has a BoundVariable with a Name field
		FString SimpleImport = FString::Printf(TEXT("(BoundVariable=(Name=\"%s\",TypeDefHandle=(RegisteredTypeIndex=-1)))"), *AttributePath);
		bSuccess = BindingProp->ImportText_Direct(*SimpleImport, PropAddr, Renderer, PPF_None) != nullptr;
	}

	GEditor->EndTransaction();

	if (bSuccess)
	{
		System->RequestCompile(false);
		UE_LOG(LogNiagaraMCPRenderer, Log, TEXT("Set renderer binding '%s' to '%s' on renderer %d"),
			*BindingName, *AttributePath, RendererIndex);
	}
	else
	{
		UE_LOG(LogNiagaraMCPRenderer, Error, TEXT("SetRendererBinding: failed to set binding '%s' to '%s'"),
			*BindingName, *AttributePath);
	}

	return bSuccess;
}
