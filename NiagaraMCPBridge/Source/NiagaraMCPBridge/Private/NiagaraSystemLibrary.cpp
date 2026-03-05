// Copyright NiagaraMCP. All Rights Reserved.

#include "NiagaraSystemLibrary.h"

#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraScriptSourceBase.h"

#include "AssetRegistry/AssetRegistryModule.h"
#include "Editor.h"
#include "Factories/Factory.h"
#include "AssetToolsModule.h"
#include "IAssetTools.h"
#include "UObject/SavePackage.h"
#include "Misc/PackageName.h"
#include "Misc/Guid.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogNiagaraMCPSystem, Log, All);

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

UNiagaraSystem* UNiagaraMCPSystemLibrary::LoadSystem(const FString& SystemPath)
{
	UNiagaraSystem* System = LoadObject<UNiagaraSystem>(nullptr, *SystemPath);
	if (!System)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("Failed to load Niagara system at path: %s"), *SystemPath);
	}
	return System;
}

int32 UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(UNiagaraSystem* System, const FString& HandleIdOrName)
{
	if (!System)
	{
		return INDEX_NONE;
	}

	const TArray<FNiagaraEmitterHandle>& Handles = System->GetEmitterHandles();

	// Try GUID first
	FGuid TestGuid;
	if (FGuid::Parse(HandleIdOrName, TestGuid))
	{
		for (int32 i = 0; i < Handles.Num(); ++i)
		{
			if (Handles[i].GetId() == TestGuid)
			{
				return i;
			}
		}
	}

	// Fall back to name match
	FName TestName(*HandleIdOrName);
	for (int32 i = 0; i < Handles.Num(); ++i)
	{
		if (Handles[i].GetName() == TestName)
		{
			return i;
		}
	}

	UE_LOG(LogNiagaraMCPSystem, Warning, TEXT("Could not find emitter handle '%s' in system '%s'"),
		*HandleIdOrName, *System->GetPathName());
	return INDEX_NONE;
}

// ─────────────────────────────────────────────────────────────────────────────
// AddEmitter
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPSystemLibrary::AddEmitter(const FString& SystemPath, const FString& EmitterAssetPath, const FString& EmitterName)
{
	UNiagaraSystem* System = LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	UNiagaraEmitter* EmitterAsset = LoadObject<UNiagaraEmitter>(nullptr, *EmitterAssetPath);
	if (!EmitterAsset)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("Failed to load emitter asset: %s"), *EmitterAssetPath);
		return FString();
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "AddEmitter", "Add Emitter"));
	System->Modify();

	FName Name = EmitterName.IsEmpty() ? EmitterAsset->GetFName() : FName(*EmitterName);
	FNiagaraEmitterHandle NewHandle = System->AddEmitterHandle(*EmitterAsset, Name);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	FString GuidStr = NewHandle.GetId().ToString();
	UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Added emitter '%s' to system '%s', handle GUID: %s"),
		*EmitterName, *SystemPath, *GuidStr);
	return GuidStr;
}

// ─────────────────────────────────────────────────────────────────────────────
// RemoveEmitter
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPSystemLibrary::RemoveEmitter(const FString& SystemPath, const FString& EmitterHandleId)
{
	UNiagaraSystem* System = LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	int32 Index = FindEmitterHandleIndex(System, EmitterHandleId);
	if (Index == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("RemoveEmitter: handle '%s' not found"), *EmitterHandleId);
		return false;
	}

	const FNiagaraEmitterHandle& Handle = System->GetEmitterHandles()[Index];

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "RemoveEmitter", "Remove Emitter"));
	System->Modify();

	System->RemoveEmitterHandle(Handle);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Removed emitter '%s' from system '%s'"),
		*EmitterHandleId, *SystemPath);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// DuplicateEmitter
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPSystemLibrary::DuplicateEmitter(const FString& SystemPath, const FString& SourceHandleId, const FString& NewName)
{
	UNiagaraSystem* System = LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	int32 Index = FindEmitterHandleIndex(System, SourceHandleId);
	if (Index == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("DuplicateEmitter: source handle '%s' not found"), *SourceHandleId);
		return FString();
	}

	const FNiagaraEmitterHandle& SourceHandle = System->GetEmitterHandles()[Index];

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "DuplicateEmitter", "Duplicate Emitter"));
	System->Modify();

	FName DupName = NewName.IsEmpty() ? FName(*(SourceHandle.GetName().ToString() + TEXT("_Copy"))) : FName(*NewName);
	FNiagaraEmitterHandle NewHandle = System->DuplicateEmitterHandle(SourceHandle, DupName);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	FString GuidStr = NewHandle.GetId().ToString();
	UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Duplicated emitter '%s' -> '%s' in system '%s', new GUID: %s"),
		*SourceHandleId, *NewName, *SystemPath, *GuidStr);
	return GuidStr;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetEmitterEnabled
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPSystemLibrary::SetEmitterEnabled(const FString& SystemPath, const FString& EmitterHandleId, bool bEnabled)
{
	UNiagaraSystem* System = LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	int32 Index = FindEmitterHandleIndex(System, EmitterHandleId);
	if (Index == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("SetEmitterEnabled: handle '%s' not found"), *EmitterHandleId);
		return false;
	}

	// GetEmitterHandles returns const ref, we need mutable access
	TArray<FNiagaraEmitterHandle>& Handles = const_cast<TArray<FNiagaraEmitterHandle>&>(System->GetEmitterHandles());
	FNiagaraEmitterHandle& Handle = Handles[Index];

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetEmitterEnabled", "Set Emitter Enabled"));
	System->Modify();

	Handle.SetIsEnabled(bEnabled, *System, true);

	GEditor->EndTransaction();

	UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Set emitter '%s' enabled=%s in system '%s'"),
		*EmitterHandleId, bEnabled ? TEXT("true") : TEXT("false"), *SystemPath);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// ReorderEmitters
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPSystemLibrary::ReorderEmitters(const FString& SystemPath, const TArray<FString>& OrderedHandleIds)
{
	UNiagaraSystem* System = LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	const TArray<FNiagaraEmitterHandle>& CurrentHandles = System->GetEmitterHandles();

	if (OrderedHandleIds.Num() != CurrentHandles.Num())
	{
		UE_LOG(LogNiagaraMCPSystem, Error,
			TEXT("ReorderEmitters: provided %d IDs but system has %d emitters"),
			OrderedHandleIds.Num(), CurrentHandles.Num());
		return false;
	}

	// Build new order
	TArray<FNiagaraEmitterHandle> NewOrder;
	NewOrder.Reserve(OrderedHandleIds.Num());

	for (const FString& Id : OrderedHandleIds)
	{
		int32 FoundIndex = FindEmitterHandleIndex(System, Id);
		if (FoundIndex == INDEX_NONE)
		{
			UE_LOG(LogNiagaraMCPSystem, Error, TEXT("ReorderEmitters: handle '%s' not found"), *Id);
			return false;
		}
		NewOrder.Add(CurrentHandles[FoundIndex]);
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "ReorderEmitters", "Reorder Emitters"));
	System->Modify();

	// Replace the emitter handles array
	TArray<FNiagaraEmitterHandle>& MutableHandles = const_cast<TArray<FNiagaraEmitterHandle>&>(System->GetEmitterHandles());
	MutableHandles = MoveTemp(NewOrder);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Reordered %d emitters in system '%s'"),
		OrderedHandleIds.Num(), *SystemPath);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetEmitterProperty
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPSystemLibrary::SetEmitterProperty(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& PropertyName, const FString& ValueJson)
{
	UNiagaraSystem* System = LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	int32 Index = FindEmitterHandleIndex(System, EmitterHandleId);
	if (Index == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("SetEmitterProperty: handle '%s' not found"), *EmitterHandleId);
		return false;
	}

	const FNiagaraEmitterHandle& Handle = System->GetEmitterHandles()[Index];
	FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData();
	if (!EmitterData)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("SetEmitterProperty: no emitter data for handle '%s'"), *EmitterHandleId);
		return false;
	}

	// Parse the JSON value
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ValueJson);
	TSharedPtr<FJsonValue> JsonValue;
	if (!FJsonSerializer::Deserialize(Reader, JsonValue) || !JsonValue.IsValid())
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("SetEmitterProperty: failed to parse JSON value: %s"), *ValueJson);
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetEmitterProp", "Set Emitter Property"));
	System->Modify();

	bool bSuccess = false;

	// Handle well-known properties
	if (PropertyName == TEXT("SimTarget") || PropertyName == TEXT("sim_target"))
	{
		FString Val = JsonValue->AsString();
		if (Val == TEXT("CPU") || Val == TEXT("CPUSim"))
		{
			EmitterData->SimTarget = ENiagaraSimTarget::CPUSim;
			bSuccess = true;
		}
		else if (Val == TEXT("GPU") || Val == TEXT("GPUComputeSim"))
		{
			EmitterData->SimTarget = ENiagaraSimTarget::GPUComputeSim;
			bSuccess = true;
		}
	}
	else if (PropertyName == TEXT("bLocalSpace") || PropertyName == TEXT("local_space"))
	{
		EmitterData->bLocalSpace = JsonValue->AsBool();
		bSuccess = true;
	}
	else if (PropertyName == TEXT("bDeterminism") || PropertyName == TEXT("determinism"))
	{
		EmitterData->bDeterminism = JsonValue->AsBool();
		bSuccess = true;
	}
	else if (PropertyName == TEXT("RandomSeed") || PropertyName == TEXT("random_seed"))
	{
		EmitterData->RandomSeed = static_cast<int32>(JsonValue->AsNumber());
		bSuccess = true;
	}
	else if (PropertyName == TEXT("AllocationMode") || PropertyName == TEXT("allocation_mode"))
	{
		FString Val = JsonValue->AsString();
		if (Val == TEXT("AutomaticEstimate"))
		{
			EmitterData->AllocationMode = EParticleAllocationMode::AutomaticEstimate;
			bSuccess = true;
		}
		else if (Val == TEXT("ManualEstimate"))
		{
			EmitterData->AllocationMode = EParticleAllocationMode::ManualEstimate;
			bSuccess = true;
		}
		else if (Val == TEXT("FixedCount"))
		{
			EmitterData->AllocationMode = EParticleAllocationMode::FixedCount;
			bSuccess = true;
		}
	}
	else if (PropertyName == TEXT("PreAllocationCount") || PropertyName == TEXT("pre_allocation_count"))
	{
		EmitterData->PreAllocationCount = static_cast<int32>(JsonValue->AsNumber());
		bSuccess = true;
	}
	else if (PropertyName == TEXT("bRequiresPersistentIDs") || PropertyName == TEXT("requires_persistent_ids"))
	{
		EmitterData->bRequiresPersistentIDs = JsonValue->AsBool();
		bSuccess = true;
	}
	else if (PropertyName == TEXT("MaxGPUParticlesSpawnPerFrame") || PropertyName == TEXT("max_gpu_particles_spawn_per_frame"))
	{
		EmitterData->MaxGPUParticlesSpawnPerFrame = static_cast<int32>(JsonValue->AsNumber());
		bSuccess = true;
	}
	else
	{
		// Try generic UObject property reflection on the emitter data struct
		// EmitterData is not a UObject, so we'd need to find the property on the owning emitter
		UE_LOG(LogNiagaraMCPSystem, Warning,
			TEXT("SetEmitterProperty: unknown property '%s'. Known properties: sim_target, local_space, determinism, random_seed, allocation_mode, pre_allocation_count, requires_persistent_ids, max_gpu_particles_spawn_per_frame"),
			*PropertyName);
	}

	GEditor->EndTransaction();

	if (bSuccess)
	{
		System->RequestCompile(false);
		UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Set emitter property '%s' on '%s' in '%s'"),
			*PropertyName, *EmitterHandleId, *SystemPath);
	}

	return bSuccess;
}

// ─────────────────────────────────────────────────────────────────────────────
// RequestCompile
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPSystemLibrary::RequestCompile(const FString& SystemPath)
{
	UNiagaraSystem* System = LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	System->RequestCompile(false);
	UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Requested compile for system '%s'"), *SystemPath);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// CreateNiagaraSystem
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPSystemLibrary::CreateNiagaraSystem(const FString& SavePath, const FString& TemplatePath)
{
	// If a template is provided, duplicate it
	if (!TemplatePath.IsEmpty())
	{
		UNiagaraSystem* Template = LoadObject<UNiagaraSystem>(nullptr, *TemplatePath);
		if (!Template)
		{
			UE_LOG(LogNiagaraMCPSystem, Error, TEXT("CreateNiagaraSystem: failed to load template '%s'"), *TemplatePath);
			return FString();
		}

		// Extract package and asset name from SavePath
		FString PackagePath, AssetName;
		int32 LastSlash;
		if (SavePath.FindLastChar('/', LastSlash))
		{
			PackagePath = SavePath.Left(LastSlash);
			AssetName = SavePath.Mid(LastSlash + 1);
		}
		else
		{
			UE_LOG(LogNiagaraMCPSystem, Error, TEXT("CreateNiagaraSystem: invalid save path '%s'"), *SavePath);
			return FString();
		}

		IAssetTools& AssetTools = FModuleManager::LoadModuleChecked<FAssetToolsModule>("AssetTools").Get();

		UObject* DuplicatedAsset = AssetTools.DuplicateAsset(AssetName, PackagePath, Template);
		if (!DuplicatedAsset)
		{
			UE_LOG(LogNiagaraMCPSystem, Error, TEXT("CreateNiagaraSystem: failed to duplicate template"));
			return FString();
		}

		FString ResultPath = DuplicatedAsset->GetPathName();
		UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Created Niagara system from template at '%s'"), *ResultPath);
		return ResultPath;
	}

	// Create a blank system
	FString PackagePath, AssetName;
	int32 LastSlash;
	if (SavePath.FindLastChar('/', LastSlash))
	{
		PackagePath = SavePath.Left(LastSlash);
		AssetName = SavePath.Mid(LastSlash + 1);
	}
	else
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("CreateNiagaraSystem: invalid save path '%s'"), *SavePath);
		return FString();
	}

	FString FullPackagePath = PackagePath / AssetName;
	UPackage* Package = CreatePackage(*FullPackagePath);
	if (!Package)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("CreateNiagaraSystem: failed to create package '%s'"), *FullPackagePath);
		return FString();
	}

	UNiagaraSystem* NewSystem = NewObject<UNiagaraSystem>(Package, FName(*AssetName),
		RF_Public | RF_Standalone | RF_Transactional);

	if (!NewSystem)
	{
		UE_LOG(LogNiagaraMCPSystem, Error, TEXT("CreateNiagaraSystem: failed to create system object"));
		return FString();
	}

	// Notify asset registry
	FAssetRegistryModule::AssetCreated(NewSystem);
	Package->MarkPackageDirty();

	FString ResultPath = NewSystem->GetPathName();
	UE_LOG(LogNiagaraMCPSystem, Log, TEXT("Created blank Niagara system at '%s'"), *ResultPath);
	return ResultPath;
}
