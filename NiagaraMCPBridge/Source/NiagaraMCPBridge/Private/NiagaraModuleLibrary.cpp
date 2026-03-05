// Copyright NiagaraMCP. All Rights Reserved.

#include "NiagaraModuleLibrary.h"
#include "NiagaraSystemLibrary.h"

#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraScript.h"
#include "NiagaraScriptSource.h"
#include "NiagaraGraph.h"
#include "NiagaraNodeOutput.h"
#include "NiagaraNodeFunctionCall.h"
#include "NiagaraNodeCustomHlsl.h"
#include "NiagaraNodeInput.h"
#include "NiagaraDataInterface.h"
#include "NiagaraConstants.h"
#include "NiagaraTypes.h"
#include "NiagaraEditorModule.h"
#include "ViewModels/Stack/NiagaraStackGraphUtilities.h"

#include "Editor.h"
#include "AssetToolsModule.h"
#include "AssetRegistry/AssetRegistryModule.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogNiagaraMCPModule, Log, All);

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

ENiagaraScriptUsage UNiagaraMCPModuleLibrary::ResolveScriptUsage(const FString& UsageString)
{
	FString Lower = UsageString.ToLower();

	if (Lower == TEXT("system_spawn") || Lower == TEXT("systemspawn"))
		return ENiagaraScriptUsage::SystemSpawnScript;
	if (Lower == TEXT("system_update") || Lower == TEXT("systemupdate"))
		return ENiagaraScriptUsage::SystemUpdateScript;
	if (Lower == TEXT("emitter_spawn") || Lower == TEXT("emitterspawn"))
		return ENiagaraScriptUsage::EmitterSpawnScript;
	if (Lower == TEXT("emitter_update") || Lower == TEXT("emitterupdate"))
		return ENiagaraScriptUsage::EmitterUpdateScript;
	if (Lower == TEXT("particle_spawn") || Lower == TEXT("particlespawn"))
		return ENiagaraScriptUsage::ParticleSpawnScript;
	if (Lower == TEXT("particle_update") || Lower == TEXT("particleupdate"))
		return ENiagaraScriptUsage::ParticleUpdateScript;

	UE_LOG(LogNiagaraMCPModule, Warning, TEXT("Unknown script usage '%s', defaulting to ParticleUpdateScript"), *UsageString);
	return ENiagaraScriptUsage::ParticleUpdateScript;
}

UNiagaraGraph* UNiagaraMCPModuleLibrary::GetGraphForUsage(UNiagaraSystem* System, const FString& EmitterHandleId, ENiagaraScriptUsage Usage)
{
	if (!System)
	{
		return nullptr;
	}

	UNiagaraScript* Script = nullptr;

	// System-level scripts
	if (Usage == ENiagaraScriptUsage::SystemSpawnScript || Usage == ENiagaraScriptUsage::SystemUpdateScript)
	{
		Script = System->GetSystemSpawnScript();
		// System spawn and update share the same graph — we just need different output nodes
		if (!Script && Usage == ENiagaraScriptUsage::SystemUpdateScript)
		{
			Script = System->GetSystemUpdateScript();
		}
	}
	else
	{
		// Emitter-level scripts
		int32 EmitterIndex = UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(System, EmitterHandleId);
		if (EmitterIndex == INDEX_NONE)
		{
			UE_LOG(LogNiagaraMCPModule, Error, TEXT("GetGraphForUsage: emitter '%s' not found"), *EmitterHandleId);
			return nullptr;
		}

		const FNiagaraEmitterHandle& Handle = System->GetEmitterHandles()[EmitterIndex];
		FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData();
		if (!EmitterData)
		{
			return nullptr;
		}

		Script = EmitterData->GetScript(Usage, FGuid());
	}

	if (!Script)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("GetGraphForUsage: no script found for usage"));
		return nullptr;
	}

	UNiagaraScriptSource* Source = Cast<UNiagaraScriptSource>(Script->GetLatestSource());
	if (!Source)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("GetGraphForUsage: script source is not UNiagaraScriptSource"));
		return nullptr;
	}

	return Source->NodeGraph;
}

UNiagaraNodeOutput* UNiagaraMCPModuleLibrary::FindOutputNode(UNiagaraSystem* System, const FString& EmitterHandleId, ENiagaraScriptUsage Usage)
{
	UNiagaraGraph* Graph = GetGraphForUsage(System, EmitterHandleId, Usage);
	if (!Graph)
	{
		return nullptr;
	}

	UNiagaraNodeOutput* OutputNode = Graph->FindEquivalentOutputNode(Usage, FGuid());
	if (!OutputNode)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("FindOutputNode: no output node found for usage"));
	}
	return OutputNode;
}

UNiagaraNodeFunctionCall* UNiagaraMCPModuleLibrary::FindModuleNode(UNiagaraSystem* System, const FString& EmitterHandleId,
	const FString& NodeGuidStr, ENiagaraScriptUsage* OutUsage)
{
	FGuid TargetGuid;
	if (!FGuid::Parse(NodeGuidStr, TargetGuid))
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("FindModuleNode: invalid GUID string '%s'"), *NodeGuidStr);
		return nullptr;
	}

	// Search across all script usages for this emitter
	static const ENiagaraScriptUsage AllUsages[] = {
		ENiagaraScriptUsage::SystemSpawnScript,
		ENiagaraScriptUsage::SystemUpdateScript,
		ENiagaraScriptUsage::EmitterSpawnScript,
		ENiagaraScriptUsage::EmitterUpdateScript,
		ENiagaraScriptUsage::ParticleSpawnScript,
		ENiagaraScriptUsage::ParticleUpdateScript,
	};

	for (ENiagaraScriptUsage Usage : AllUsages)
	{
		UNiagaraNodeOutput* OutputNode = FindOutputNode(System, EmitterHandleId, Usage);
		if (!OutputNode)
		{
			continue;
		}

		TArray<UNiagaraNodeFunctionCall*> ModuleNodes;
		FNiagaraStackGraphUtilities::GetOrderedModuleNodes(*OutputNode, ModuleNodes);

		for (UNiagaraNodeFunctionCall* Node : ModuleNodes)
		{
			if (Node && Node->NodeGuid == TargetGuid)
			{
				if (OutUsage)
				{
					*OutUsage = Usage;
				}
				return Node;
			}
		}
	}

	// Also try matching by name if the GUID didn't work — the string might be a function name
	for (ENiagaraScriptUsage Usage : AllUsages)
	{
		UNiagaraNodeOutput* OutputNode = FindOutputNode(System, EmitterHandleId, Usage);
		if (!OutputNode)
		{
			continue;
		}

		TArray<UNiagaraNodeFunctionCall*> ModuleNodes;
		FNiagaraStackGraphUtilities::GetOrderedModuleNodes(*OutputNode, ModuleNodes);

		for (UNiagaraNodeFunctionCall* Node : ModuleNodes)
		{
			if (Node && Node->GetFunctionName() == NodeGuidStr)
			{
				if (OutUsage)
				{
					*OutUsage = Usage;
				}
				return Node;
			}
		}
	}

	UE_LOG(LogNiagaraMCPModule, Error, TEXT("FindModuleNode: node '%s' not found in emitter '%s'"),
		*NodeGuidStr, *EmitterHandleId);
	return nullptr;
}

// Helper: Serialize JSON object to string
static FString JsonObjectToString(const TSharedRef<FJsonObject>& JsonObj)
{
	FString OutputString;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
	FJsonSerializer::Serialize(JsonObj, Writer);
	return OutputString;
}

// Helper: Serialize JSON array to string
static FString JsonArrayToString(const TArray<TSharedPtr<FJsonValue>>& JsonArray)
{
	FString OutputString;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&OutputString);
	FJsonSerializer::Serialize(JsonArray, Writer);
	return OutputString;
}

// ─────────────────────────────────────────────────────────────────────────────
// GetOrderedModules
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPModuleLibrary::GetOrderedModules(const FString& SystemPath, const FString& EmitterHandleId, const FString& ScriptUsage)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	ENiagaraScriptUsage Usage = ResolveScriptUsage(ScriptUsage);
	UNiagaraNodeOutput* OutputNode = FindOutputNode(System, EmitterHandleId, Usage);
	if (!OutputNode)
	{
		return FString();
	}

	TArray<UNiagaraNodeFunctionCall*> ModuleNodes;
	FNiagaraStackGraphUtilities::GetOrderedModuleNodes(*OutputNode, ModuleNodes);

	TArray<TSharedPtr<FJsonValue>> JsonArray;
	for (int32 i = 0; i < ModuleNodes.Num(); ++i)
	{
		UNiagaraNodeFunctionCall* Node = ModuleNodes[i];
		if (!Node)
		{
			continue;
		}

		TSharedRef<FJsonObject> ModuleObj = MakeShared<FJsonObject>();
		ModuleObj->SetStringField(TEXT("node_guid"), Node->NodeGuid.ToString());
		ModuleObj->SetStringField(TEXT("function_name"), Node->GetFunctionName());
		ModuleObj->SetNumberField(TEXT("index"), i);
		TOptional<bool> bModEnabled = FNiagaraStackGraphUtilities::GetModuleIsEnabled(*Node);
		ModuleObj->SetBoolField(TEXT("enabled"), bModEnabled.IsSet() ? bModEnabled.GetValue() : true);

		// Script reference
		if (Node->FunctionScript)
		{
			ModuleObj->SetStringField(TEXT("script_path"), Node->FunctionScript->GetPathName());
		}

		JsonArray.Add(MakeShared<FJsonValueObject>(ModuleObj));
	}

	return JsonArrayToString(JsonArray);
}

// ─────────────────────────────────────────────────────────────────────────────
// GetModuleInputs
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPModuleLibrary::GetModuleInputs(const FString& SystemPath, const FString& EmitterHandleId, const FString& ModuleNodeGuid)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	ENiagaraScriptUsage FoundUsage;
	UNiagaraNodeFunctionCall* ModuleNode = FindModuleNode(System, EmitterHandleId, ModuleNodeGuid, &FoundUsage);
	if (!ModuleNode)
	{
		return FString();
	}

	// Get the function inputs using stack graph utilities
	TArray<FNiagaraVariable> Inputs;
	FNiagaraStackGraphUtilities::GetStackFunctionInputs(*ModuleNode, Inputs,
		FNiagaraStackGraphUtilities::ENiagaraGetStackFunctionInputPinsOptions::ModuleInputsOnly, false);

	TArray<TSharedPtr<FJsonValue>> JsonArray;
	for (const FNiagaraVariable& Input : Inputs)
	{
		TSharedRef<FJsonObject> InputObj = MakeShared<FJsonObject>();
		InputObj->SetStringField(TEXT("name"), Input.GetName().ToString());
		InputObj->SetStringField(TEXT("type"), Input.GetType().GetName());

		// Check for linked/bound inputs
		// Read the override pin value if available
		FNiagaraParameterHandle AliasedHandle = FNiagaraParameterHandle::CreateAliasedModuleParameterHandle(
			FNiagaraParameterHandle(Input.GetName()), ModuleNode);
		UEdGraphPin* OverridePin = FNiagaraStackGraphUtilities::GetStackFunctionInputOverridePin(
			*ModuleNode, AliasedHandle);

		if (OverridePin)
		{
			InputObj->SetStringField(TEXT("override_value"), OverridePin->DefaultValue);
			InputObj->SetBoolField(TEXT("has_override"), true);

			// Check if the override is a linked parameter
			if (OverridePin->LinkedTo.Num() > 0)
			{
				InputObj->SetBoolField(TEXT("is_linked"), true);
				if (UNiagaraNodeInput* LinkedInput = Cast<UNiagaraNodeInput>(OverridePin->LinkedTo[0]->GetOwningNode()))
				{
					InputObj->SetStringField(TEXT("linked_parameter"), LinkedInput->Input.GetName().ToString());
				}
			}
		}
		else
		{
			InputObj->SetBoolField(TEXT("has_override"), false);
		}

		JsonArray.Add(MakeShared<FJsonValueObject>(InputObj));
	}

	return JsonArrayToString(JsonArray);
}

// ─────────────────────────────────────────────────────────────────────────────
// GetModuleGraph
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPModuleLibrary::GetModuleGraph(const FString& ModuleScriptPath)
{
	UNiagaraScript* Script = LoadObject<UNiagaraScript>(nullptr, *ModuleScriptPath);
	if (!Script)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("GetModuleGraph: failed to load script '%s'"), *ModuleScriptPath);
		return FString();
	}

	UNiagaraScriptSource* Source = Cast<UNiagaraScriptSource>(Script->GetLatestSource());
	if (!Source || !Source->NodeGraph)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("GetModuleGraph: no graph available for '%s'"), *ModuleScriptPath);
		return FString();
	}

	UNiagaraGraph* Graph = Source->NodeGraph;
	TSharedRef<FJsonObject> ResultObj = MakeShared<FJsonObject>();
	ResultObj->SetStringField(TEXT("script_path"), ModuleScriptPath);
	ResultObj->SetStringField(TEXT("script_usage"), StaticEnum<ENiagaraScriptUsage>()->GetNameStringByValue(static_cast<int64>(Script->GetUsage())));

	// Walk the nodes
	TArray<TSharedPtr<FJsonValue>> NodesArray;
	TArray<UEdGraphNode*> AllNodes;
	Graph->GetNodesOfClass<UEdGraphNode>(AllNodes);

	for (UEdGraphNode* Node : AllNodes)
	{
		TSharedRef<FJsonObject> NodeObj = MakeShared<FJsonObject>();
		NodeObj->SetStringField(TEXT("node_guid"), Node->NodeGuid.ToString());
		NodeObj->SetStringField(TEXT("class"), Node->GetClass()->GetName());
		NodeObj->SetStringField(TEXT("title"), Node->GetNodeTitle(ENodeTitleType::FullTitle).ToString());
		NodeObj->SetNumberField(TEXT("pos_x"), Node->NodePosX);
		NodeObj->SetNumberField(TEXT("pos_y"), Node->NodePosY);

		// Special handling for function call nodes
		if (UNiagaraNodeFunctionCall* FuncNode = Cast<UNiagaraNodeFunctionCall>(Node))
		{
			NodeObj->SetStringField(TEXT("function_name"), FuncNode->GetFunctionName());
			if (FuncNode->FunctionScript)
			{
				NodeObj->SetStringField(TEXT("function_script"), FuncNode->FunctionScript->GetPathName());
			}
		}

		// Pins
		TArray<TSharedPtr<FJsonValue>> PinsArray;
		for (UEdGraphPin* Pin : Node->Pins)
		{
			TSharedRef<FJsonObject> PinObj = MakeShared<FJsonObject>();
			PinObj->SetStringField(TEXT("name"), Pin->PinName.ToString());
			PinObj->SetStringField(TEXT("direction"), Pin->Direction == EGPD_Input ? TEXT("Input") : TEXT("Output"));
			PinObj->SetStringField(TEXT("type"), Pin->PinType.PinCategory.ToString());
			PinObj->SetStringField(TEXT("default_value"), Pin->DefaultValue);
			PinObj->SetNumberField(TEXT("linked_count"), Pin->LinkedTo.Num());
			PinsArray.Add(MakeShared<FJsonValueObject>(PinObj));
		}
		NodeObj->SetArrayField(TEXT("pins"), PinsArray);

		NodesArray.Add(MakeShared<FJsonValueObject>(NodeObj));
	}
	ResultObj->SetArrayField(TEXT("nodes"), NodesArray);

	return JsonObjectToString(ResultObj);
}

// ─────────────────────────────────────────────────────────────────────────────
// AddModule
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPModuleLibrary::AddModule(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& ScriptUsage, const FString& ModuleScriptPath, int32 Index)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	UNiagaraScript* ModuleScript = LoadObject<UNiagaraScript>(nullptr, *ModuleScriptPath);
	if (!ModuleScript)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("AddModule: failed to load module script '%s'"), *ModuleScriptPath);
		return FString();
	}

	ENiagaraScriptUsage Usage = ResolveScriptUsage(ScriptUsage);
	UNiagaraNodeOutput* OutputNode = FindOutputNode(System, EmitterHandleId, Usage);
	if (!OutputNode)
	{
		return FString();
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "AddModule", "Add Module"));
	System->Modify();

	UNiagaraNodeFunctionCall* NewNode = FNiagaraStackGraphUtilities::AddScriptModuleToStack(ModuleScript, *OutputNode, Index);

	GEditor->EndTransaction();

	if (!NewNode)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("AddModule: AddScriptModuleToStack failed"));
		return FString();
	}

	System->RequestCompile(false);

	FString GuidStr = NewNode->NodeGuid.ToString();
	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Added module '%s' to stage '%s', node GUID: %s"),
		*ModuleScriptPath, *ScriptUsage, *GuidStr);
	return GuidStr;
}

// ─────────────────────────────────────────────────────────────────────────────
// RemoveModule
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPModuleLibrary::RemoveModule(const FString& SystemPath, const FString& EmitterHandleId, const FString& ModuleNodeGuid)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	ENiagaraScriptUsage FoundUsage;
	UNiagaraNodeFunctionCall* ModuleNode = FindModuleNode(System, EmitterHandleId, ModuleNodeGuid, &FoundUsage);
	if (!ModuleNode)
	{
		return false;
	}

	// Find the emitter GUID for RemoveModuleFromStack
	FGuid EmitterGuid;
	int32 EmitterIndex = UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(System, EmitterHandleId);
	if (EmitterIndex != INDEX_NONE)
	{
		EmitterGuid = System->GetEmitterHandles()[EmitterIndex].GetId();
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "RemoveModule", "Remove Module"));
	System->Modify();

	FNiagaraStackGraphUtilities::RemoveModuleFromStack(*System, EmitterGuid, *ModuleNode);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Removed module '%s' from emitter '%s' in system '%s'"),
		*ModuleNodeGuid, *EmitterHandleId, *SystemPath);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// MoveModule
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPModuleLibrary::MoveModule(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& ModuleNodeGuid, int32 NewIndex)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	ENiagaraScriptUsage FoundUsage;
	UNiagaraNodeFunctionCall* ModuleNode = FindModuleNode(System, EmitterHandleId, ModuleNodeGuid, &FoundUsage);
	if (!ModuleNode)
	{
		return false;
	}

	// Find the output node for the discovered usage
	UNiagaraNodeOutput* OutputNode = FindOutputNode(System, EmitterHandleId, FoundUsage);
	if (!OutputNode)
	{
		return false;
	}

	// Get the current ordered modules to find this module's position
	TArray<UNiagaraNodeFunctionCall*> ModuleNodes;
	FNiagaraStackGraphUtilities::GetOrderedModuleNodes(*OutputNode, ModuleNodes);

	int32 CurrentIndex = ModuleNodes.IndexOfByKey(ModuleNode);
	if (CurrentIndex == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("MoveModule: module node not found in ordered list"));
		return false;
	}

	if (NewIndex == CurrentIndex)
	{
		// Already at the target position
		return true;
	}

	// Clamp NewIndex to valid range
	NewIndex = FMath::Clamp(NewIndex, 0, ModuleNodes.Num() - 1);

	// Get the module script reference before removal
	UNiagaraScript* ModuleScript = ModuleNode->FunctionScript;
	if (!ModuleScript)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("MoveModule: module node has no script reference"));
		return false;
	}

	// Find the emitter GUID for RemoveModuleFromStack
	FGuid EmitterGuid;
	int32 EmitterIndex = UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(System, EmitterHandleId);
	if (EmitterIndex != INDEX_NONE)
	{
		EmitterGuid = System->GetEmitterHandles()[EmitterIndex].GetId();
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "MoveModule", "Move Module"));
	System->Modify();

	// Step 1: Remove the module from the stack
	FNiagaraStackGraphUtilities::RemoveModuleFromStack(*System, EmitterGuid, *ModuleNode);

	// Step 2: Re-add at the new position
	UNiagaraNodeFunctionCall* NewNode = FNiagaraStackGraphUtilities::AddScriptModuleToStack(ModuleScript, *OutputNode, NewIndex);

	GEditor->EndTransaction();

	if (!NewNode)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("MoveModule: failed to re-add module at new index %d"), NewIndex);
		return false;
	}

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Moved module '%s' from index %d to index %d"), *ModuleNodeGuid, CurrentIndex, NewIndex);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetModuleEnabled
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPModuleLibrary::SetModuleEnabled(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& ModuleNodeGuid, bool bEnabled)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	UNiagaraNodeFunctionCall* ModuleNode = FindModuleNode(System, EmitterHandleId, ModuleNodeGuid);
	if (!ModuleNode)
	{
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetModuleEnabled", "Set Module Enabled"));
	System->Modify();

	FNiagaraStackGraphUtilities::SetModuleIsEnabled(*ModuleNode, bEnabled);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Set module '%s' enabled=%s"),
		*ModuleNodeGuid, bEnabled ? TEXT("true") : TEXT("false"));
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetModuleInputValue
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPModuleLibrary::SetModuleInputValue(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& ModuleNodeGuid, const FString& InputName, const FString& ValueJson)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	UNiagaraNodeFunctionCall* ModuleNode = FindModuleNode(System, EmitterHandleId, ModuleNodeGuid);
	if (!ModuleNode)
	{
		return false;
	}

	// Find the matching input variable to get its type
	TArray<FNiagaraVariable> Inputs;
	FNiagaraStackGraphUtilities::GetStackFunctionInputs(*ModuleNode, Inputs,
		FNiagaraStackGraphUtilities::ENiagaraGetStackFunctionInputPinsOptions::ModuleInputsOnly, false);

	FNiagaraTypeDefinition InputType = FNiagaraTypeDefinition::GetFloatDef();
	for (const FNiagaraVariable& Input : Inputs)
	{
		if (Input.GetName() == FName(*InputName))
		{
			InputType = Input.GetType();
			break;
		}
	}

	// Alias the handle for override pin lookup
	FNiagaraParameterHandle AliasedHandle = FNiagaraParameterHandle::CreateAliasedModuleParameterHandle(
		FNiagaraParameterHandle(FName(*InputName)), ModuleNode);

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetModuleInput", "Set Module Input Value"));
	System->Modify();

	// Parse JSON value
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ValueJson);
	TSharedPtr<FJsonValue> JsonValue;
	if (!FJsonSerializer::Deserialize(Reader, JsonValue) || !JsonValue.IsValid())
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("SetModuleInputValue: failed to parse JSON: %s"), *ValueJson);
		GEditor->EndTransaction();
		return false;
	}

	// Get or create override pin (returns ref)
	UEdGraphPin& MutableOverridePin = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(
		*ModuleNode, AliasedHandle, InputType, FGuid(), FGuid());

	// Set the pin default value from JSON
	// The pin default value is a string representation
	FString ValueStr;
	if (JsonValue->Type == EJson::Number)
	{
		ValueStr = FString::SanitizeFloat(JsonValue->AsNumber());
	}
	else if (JsonValue->Type == EJson::Boolean)
	{
		ValueStr = JsonValue->AsBool() ? TEXT("true") : TEXT("false");
	}
	else if (JsonValue->Type == EJson::String)
	{
		ValueStr = JsonValue->AsString();
	}
	else if (JsonValue->Type == EJson::Object)
	{
		// For vectors, colors, etc. — serialize back to string
		TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
		if (Obj->HasField(TEXT("x")))
		{
			// Vector-like: x,y,z or x,y,z,w
			double X = Obj->GetNumberField(TEXT("x"));
			double Y = Obj->GetNumberField(TEXT("y"));
			double Z = Obj->HasField(TEXT("z")) ? Obj->GetNumberField(TEXT("z")) : 0.0;
			double W = Obj->HasField(TEXT("w")) ? Obj->GetNumberField(TEXT("w")) : 0.0;

			if (Obj->HasField(TEXT("w")))
			{
				ValueStr = FString::Printf(TEXT("%f,%f,%f,%f"), X, Y, Z, W);
			}
			else if (Obj->HasField(TEXT("z")))
			{
				ValueStr = FString::Printf(TEXT("%f,%f,%f"), X, Y, Z);
			}
			else
			{
				ValueStr = FString::Printf(TEXT("%f,%f"), X, Y);
			}
		}
		else if (Obj->HasField(TEXT("r")))
		{
			// Color: r,g,b,a
			double R = Obj->GetNumberField(TEXT("r"));
			double G = Obj->GetNumberField(TEXT("g"));
			double B = Obj->GetNumberField(TEXT("b"));
			double A = Obj->HasField(TEXT("a")) ? Obj->GetNumberField(TEXT("a")) : 1.0;
			ValueStr = FString::Printf(TEXT("%f,%f,%f,%f"), R, G, B, A);
		}
		else
		{
			// Generic: serialize as JSON string
			TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&ValueStr);
			FJsonSerializer::Serialize(Obj.ToSharedRef(), Writer);
		}
	}
	else
	{
		ValueStr = ValueJson;
	}

	MutableOverridePin.DefaultValue = ValueStr;

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Set module input '%s' = '%s' on node '%s'"),
		*InputName, *ValueStr, *ModuleNodeGuid);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetModuleInputBinding
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPModuleLibrary::SetModuleInputBinding(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& ModuleNodeGuid, const FString& InputName, const FString& BindingPath)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	UNiagaraNodeFunctionCall* ModuleNode = FindModuleNode(System, EmitterHandleId, ModuleNodeGuid);
	if (!ModuleNode)
	{
		return false;
	}

	// Find the matching input variable to get its type
	TArray<FNiagaraVariable> Inputs;
	FNiagaraStackGraphUtilities::GetStackFunctionInputs(*ModuleNode, Inputs,
		FNiagaraStackGraphUtilities::ENiagaraGetStackFunctionInputPinsOptions::ModuleInputsOnly, false);

	FNiagaraTypeDefinition InputType = FNiagaraTypeDefinition::GetFloatDef();
	for (const FNiagaraVariable& Input : Inputs)
	{
		if (Input.GetName() == FName(*InputName))
		{
			InputType = Input.GetType();
			break;
		}
	}

	// Alias the handle for override pin lookup
	FNiagaraParameterHandle AliasedHandle = FNiagaraParameterHandle::CreateAliasedModuleParameterHandle(
		FNiagaraParameterHandle(FName(*InputName)), ModuleNode);

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetModuleBinding", "Set Module Input Binding"));
	System->Modify();

	// Get or create the override pin
	UEdGraphPin& OverridePin = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(
		*ModuleNode, AliasedHandle, InputType, FGuid(), FGuid());

	// Create the linked parameter variable
	FNiagaraVariable LinkedParam(InputType, FName(*BindingPath));

	// Get known parameters for context
	UNiagaraGraph* Graph = ModuleNode->GetNiagaraGraph();
	TSet<FNiagaraVariableBase> KnownParameters;
	if (Graph)
	{
		FNiagaraStackGraphUtilities::GetParametersForContext(Graph, *System, KnownParameters);
	}

	// Use the stack graph utility to set the linked parameter value
	FNiagaraStackGraphUtilities::SetLinkedParameterValueForFunctionInput(
		OverridePin, LinkedParam, KnownParameters);

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Bound module input '%s' to '%s' on node '%s'"),
		*InputName, *BindingPath, *ModuleNodeGuid);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetModuleInputDI
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPModuleLibrary::SetModuleInputDI(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& ModuleNodeGuid, const FString& InputName,
	const FString& DIClass, const FString& DIConfigJson)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	UNiagaraNodeFunctionCall* ModuleNode = FindModuleNode(System, EmitterHandleId, ModuleNodeGuid);
	if (!ModuleNode)
	{
		return false;
	}

	// Find the DI class
	FString FullClassName = DIClass;
	if (!FullClassName.StartsWith(TEXT("UNiagara")))
	{
		FullClassName = TEXT("UNiagara") + DIClass;
	}
	if (!FullClassName.EndsWith(TEXT("DataInterface")) && !FullClassName.Contains(TEXT("DataInterface")))
	{
		// Try common patterns
	}

	UClass* DIUClass = FindFirstObject<UClass>(*FullClassName, EFindFirstObjectOptions::NativeFirst);
	if (!DIUClass)
	{
		// Try without U prefix
		FString WithoutU = FullClassName.Mid(1);
		DIUClass = FindFirstObject<UClass>(*WithoutU, EFindFirstObjectOptions::NativeFirst);
	}
	if (!DIUClass)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("SetModuleInputDI: could not find DI class '%s'"), *DIClass);
		return false;
	}

	// Find the matching input variable to get its type
	TArray<FNiagaraVariable> Inputs;
	FNiagaraStackGraphUtilities::GetStackFunctionInputs(*ModuleNode, Inputs,
		FNiagaraStackGraphUtilities::ENiagaraGetStackFunctionInputPinsOptions::ModuleInputsOnly, false);

	FNiagaraTypeDefinition InputType(DIUClass);
	for (const FNiagaraVariable& Input : Inputs)
	{
		if (Input.GetName() == FName(*InputName))
		{
			InputType = Input.GetType();
			break;
		}
	}

	// Alias the handle for override pin lookup
	FNiagaraParameterHandle AliasedHandle = FNiagaraParameterHandle::CreateAliasedModuleParameterHandle(
		FNiagaraParameterHandle(FName(*InputName)), ModuleNode);

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetModuleInputDI", "Set Module Input Data Interface"));
	System->Modify();

	// Get or create the override pin
	UEdGraphPin& OverridePin = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(
		*ModuleNode, AliasedHandle, InputType, FGuid(), FGuid());

	// SetDataInterfaceValueForFunctionInput creates the DI for us
	UNiagaraDataInterface* DIInstance = nullptr;
	FNiagaraStackGraphUtilities::SetDataInterfaceValueForFunctionInput(
		OverridePin, DIUClass, InputName, DIInstance);

	// Apply configuration from JSON if provided
	if (DIInstance && !DIConfigJson.IsEmpty())
	{
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(DIConfigJson);
		TSharedPtr<FJsonObject> ConfigObj;
		if (FJsonSerializer::Deserialize(Reader, ConfigObj) && ConfigObj.IsValid())
		{
			// Set properties via reflection
			for (auto& Pair : ConfigObj->Values)
			{
				FProperty* Prop = DIUClass->FindPropertyByName(FName(*Pair.Key));
				if (Prop)
				{
					void* PropAddr = Prop->ContainerPtrToValuePtr<void>(DIInstance);
					if (FFloatProperty* FloatProp = CastField<FFloatProperty>(Prop))
					{
						FloatProp->SetPropertyValue(PropAddr, static_cast<float>(Pair.Value->AsNumber()));
					}
					else if (FIntProperty* IntProp = CastField<FIntProperty>(Prop))
					{
						IntProp->SetPropertyValue(PropAddr, static_cast<int32>(Pair.Value->AsNumber()));
					}
					else if (FBoolProperty* BoolProp = CastField<FBoolProperty>(Prop))
					{
						BoolProp->SetPropertyValue(PropAddr, Pair.Value->AsBool());
					}
					else if (FStrProperty* StrProp = CastField<FStrProperty>(Prop))
					{
						StrProp->SetPropertyValue(PropAddr, Pair.Value->AsString());
					}
				}
			}
		}
	}

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Set DI '%s' on module input '%s' of node '%s'"),
		*DIClass, *InputName, *ModuleNodeGuid);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// CreateModuleFromHLSL / CreateFunctionFromHLSL
// ─────────────────────────────────────────────────────────────────────────────

static FString CreateScriptFromHLSLInternal(const FString& SavePath, const FString& HLSLCode,
	const FString& InputsJson, const FString& OutputsJson, ENiagaraScriptUsage ScriptUsage)
{
	// Parse inputs
	TSharedRef<TJsonReader<>> InputReader = TJsonReaderFactory<>::Create(InputsJson);
	TArray<TSharedPtr<FJsonValue>> InputsArray;
	if (!FJsonSerializer::Deserialize(InputReader, InputsArray))
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("CreateScriptFromHLSL: failed to parse inputs JSON"));
		return FString();
	}

	// Parse outputs
	TSharedRef<TJsonReader<>> OutputReader = TJsonReaderFactory<>::Create(OutputsJson);
	TArray<TSharedPtr<FJsonValue>> OutputsArray;
	if (!FJsonSerializer::Deserialize(OutputReader, OutputsArray))
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("CreateScriptFromHLSL: failed to parse outputs JSON"));
		return FString();
	}

	// Extract package path and asset name
	FString PackagePath, AssetName;
	int32 LastSlash;
	if (SavePath.FindLastChar('/', LastSlash))
	{
		PackagePath = SavePath.Left(LastSlash);
		AssetName = SavePath.Mid(LastSlash + 1);
	}
	else
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("CreateScriptFromHLSL: invalid save path '%s'"), *SavePath);
		return FString();
	}

	FString FullPackagePath = PackagePath / AssetName;
	UPackage* Package = CreatePackage(*FullPackagePath);
	if (!Package)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("CreateScriptFromHLSL: failed to create package"));
		return FString();
	}

	// Create the script
	UNiagaraScript* NewScript = NewObject<UNiagaraScript>(Package, FName(*AssetName),
		RF_Public | RF_Standalone | RF_Transactional);
	if (!NewScript)
	{
		UE_LOG(LogNiagaraMCPModule, Error, TEXT("CreateScriptFromHLSL: failed to create script"));
		return FString();
	}

	NewScript->SetUsage(ScriptUsage);

	// Create a script source with a graph
	UNiagaraScriptSource* Source = NewObject<UNiagaraScriptSource>(NewScript, "ScriptSource",
		RF_Transactional);
	Source->NodeGraph = NewObject<UNiagaraGraph>(Source, "NiagaraGraph", RF_Transactional);
	NewScript->SetLatestSource(Source);

	// Create output node
	UNiagaraNodeOutput* OutputNode = NewObject<UNiagaraNodeOutput>(Source->NodeGraph);
	OutputNode->SetUsage(ScriptUsage);
	Source->NodeGraph->AddNode(OutputNode, false, false);

	// Create a Custom HLSL node
	UNiagaraNodeCustomHlsl* HLSLNode = NewObject<UNiagaraNodeCustomHlsl>(Source->NodeGraph);
	Source->NodeGraph->AddNode(HLSLNode, false, false);

	// Set the custom HLSL code
	HLSLNode->SetCustomHlsl(HLSLCode);
	HLSLNode->ScriptUsage = ScriptUsage;

	// Helper lambda to resolve type string to FNiagaraTypeDefinition
	auto ResolveType = [](const FString& TypeLower) -> FNiagaraTypeDefinition
	{
		if (TypeLower == TEXT("float"))
			return FNiagaraTypeDefinition::GetFloatDef();
		if (TypeLower == TEXT("int") || TypeLower == TEXT("int32"))
			return FNiagaraTypeDefinition::GetIntDef();
		if (TypeLower == TEXT("bool"))
			return FNiagaraTypeDefinition::GetBoolDef();
		if (TypeLower == TEXT("vec2") || TypeLower == TEXT("vector2d"))
			return FNiagaraTypeDefinition::GetVec2Def();
		if (TypeLower == TEXT("vec3") || TypeLower == TEXT("vector"))
			return FNiagaraTypeDefinition::GetVec3Def();
		if (TypeLower == TEXT("vec4") || TypeLower == TEXT("vector4"))
			return FNiagaraTypeDefinition::GetVec4Def();
		if (TypeLower == TEXT("color") || TypeLower == TEXT("linearcolor"))
			return FNiagaraTypeDefinition::GetColorDef();
		if (TypeLower == TEXT("position"))
			return FNiagaraTypeDefinition::GetPositionDef();
		if (TypeLower == TEXT("quat") || TypeLower == TEXT("quaternion"))
			return FNiagaraTypeDefinition::GetQuatDef();
		if (TypeLower == TEXT("matrix") || TypeLower == TEXT("matrix4"))
			return FNiagaraTypeDefinition::GetMatrix4Def();
		return FNiagaraTypeDefinition::GetFloatDef();
	};

	// Add input pins via RequestNewTypedPin
	for (const TSharedPtr<FJsonValue>& InputVal : InputsArray)
	{
		TSharedPtr<FJsonObject> InputObj = InputVal->AsObject();
		if (!InputObj)
		{
			continue;
		}
		FString Name = InputObj->GetStringField(TEXT("name"));
		FString Type = InputObj->GetStringField(TEXT("type"));
		FNiagaraTypeDefinition TypeDef = ResolveType(Type.ToLower());

		HLSLNode->RequestNewTypedPin(EGPD_Input, TypeDef, FName(*Name));
	}

	// Add output pins via RequestNewTypedPin
	for (const TSharedPtr<FJsonValue>& OutputVal : OutputsArray)
	{
		TSharedPtr<FJsonObject> OutputObj = OutputVal->AsObject();
		if (!OutputObj)
		{
			continue;
		}
		FString Name = OutputObj->GetStringField(TEXT("name"));
		FString Type = OutputObj->GetStringField(TEXT("type"));
		FNiagaraTypeDefinition TypeDef = ResolveType(Type.ToLower());

		HLSLNode->RequestNewTypedPin(EGPD_Output, TypeDef, FName(*Name));
	}

	// Wire the HLSL node outputs to the output node inputs
	HLSLNode->RefreshFromExternalChanges();
	OutputNode->RefreshFromExternalChanges();

	// Notify asset registry
	FAssetRegistryModule::AssetCreated(NewScript);
	Package->MarkPackageDirty();

	FString ResultPath = NewScript->GetPathName();
	UE_LOG(LogNiagaraMCPModule, Log, TEXT("Created script from HLSL at '%s'"), *ResultPath);
	return ResultPath;
}

FString UNiagaraMCPModuleLibrary::CreateModuleFromHLSL(const FString& SavePath, const FString& HLSLCode,
	const FString& InputsJson, const FString& OutputsJson)
{
	return CreateScriptFromHLSLInternal(SavePath, HLSLCode, InputsJson, OutputsJson, ENiagaraScriptUsage::Module);
}

FString UNiagaraMCPModuleLibrary::CreateFunctionFromHLSL(const FString& SavePath, const FString& HLSLCode,
	const FString& InputsJson, const FString& OutputsJson)
{
	return CreateScriptFromHLSLInternal(SavePath, HLSLCode, InputsJson, OutputsJson, ENiagaraScriptUsage::Function);
}
