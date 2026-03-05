// Copyright NiagaraMCP. All Rights Reserved.

#include "NiagaraBatchLibrary.h"
#include "NiagaraSystemLibrary.h"
#include "NiagaraModuleLibrary.h"
#include "NiagaraParameterLibrary.h"
#include "NiagaraRendererLibrary.h"

#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"

#include "Editor.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogNiagaraMCPBatch, Log, All);

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

static FString BatchJsonToString(const TSharedRef<FJsonObject>& Obj)
{
	FString Result;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
	FJsonSerializer::Serialize(Obj, Writer);
	return Result;
}

/** Serialize a JsonValue back to a string for passing to sub-libraries. */
static FString JsonValueToString(const TSharedPtr<FJsonValue>& Value)
{
	if (!Value.IsValid())
	{
		return FString();
	}

	if (Value->Type == EJson::String)
	{
		// Wrap in quotes for JSON
		return FString::Printf(TEXT("\"%s\""), *Value->AsString());
	}
	else if (Value->Type == EJson::Number)
	{
		return FString::SanitizeFloat(Value->AsNumber());
	}
	else if (Value->Type == EJson::Boolean)
	{
		return Value->AsBool() ? TEXT("true") : TEXT("false");
	}
	else if (Value->Type == EJson::Object || Value->Type == EJson::Array)
	{
		FString Result;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
		if (Value->Type == EJson::Object)
		{
			FJsonSerializer::Serialize(Value->AsObject().ToSharedRef(), Writer);
		}
		else
		{
			FJsonSerializer::Serialize(Value->AsArray(), Writer);
		}
		return Result;
	}

	return FString();
}

/** Serialize a JsonValue for use as a raw value string (no extra quoting for strings). */
static FString JsonValueToRawString(const TSharedPtr<FJsonValue>& Value)
{
	if (!Value.IsValid())
	{
		return FString();
	}

	if (Value->Type == EJson::String)
	{
		return Value->AsString();
	}

	return JsonValueToString(Value);
}

// ─────────────────────────────────────────────────────────────────────────────
// BatchExecute
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPBatchLibrary::BatchExecute(const FString& SystemPath, const FString& OperationsJson)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		TSharedRef<FJsonObject> ErrorObj = MakeShared<FJsonObject>();
		ErrorObj->SetBoolField(TEXT("success"), false);
		ErrorObj->SetStringField(TEXT("error"), TEXT("Failed to load system"));
		return BatchJsonToString(ErrorObj);
	}

	// Parse operations array
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(OperationsJson);
	TArray<TSharedPtr<FJsonValue>> Operations;
	if (!FJsonSerializer::Deserialize(Reader, Operations))
	{
		TSharedRef<FJsonObject> ErrorObj = MakeShared<FJsonObject>();
		ErrorObj->SetBoolField(TEXT("success"), false);
		ErrorObj->SetStringField(TEXT("error"), TEXT("Failed to parse operations JSON"));
		return BatchJsonToString(ErrorObj);
	}

	// Wrap ALL operations in a single transaction
	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "BatchExecute", "Batch Execute Niagara Operations"));
	System->Modify();

	TArray<TSharedPtr<FJsonValue>> ResultsArray;
	int32 SuccessCount = 0;
	int32 FailCount = 0;

	for (int32 i = 0; i < Operations.Num(); ++i)
	{
		TSharedPtr<FJsonObject> OpObj = Operations[i]->AsObject();
		if (!OpObj.IsValid())
		{
			TSharedRef<FJsonObject> ResultObj = MakeShared<FJsonObject>();
			ResultObj->SetNumberField(TEXT("index"), i);
			ResultObj->SetBoolField(TEXT("success"), false);
			ResultObj->SetStringField(TEXT("error"), TEXT("Invalid operation object"));
			ResultsArray.Add(MakeShared<FJsonValueObject>(ResultObj));
			FailCount++;
			continue;
		}

		FString Op = OpObj->GetStringField(TEXT("op"));
		TSharedRef<FJsonObject> ResultObj = MakeShared<FJsonObject>();
		ResultObj->SetNumberField(TEXT("index"), i);
		ResultObj->SetStringField(TEXT("op"), Op);

		bool bOpSuccess = false;

		if (Op == TEXT("add_emitter"))
		{
			FString EmitterAsset = OpObj->GetStringField(TEXT("emitter_asset"));
			FString EmitterName = OpObj->HasField(TEXT("name")) ? OpObj->GetStringField(TEXT("name")) : FString();
			FString HandleId = UNiagaraMCPSystemLibrary::AddEmitter(SystemPath, EmitterAsset, EmitterName);
			bOpSuccess = !HandleId.IsEmpty();
			if (bOpSuccess)
			{
				ResultObj->SetStringField(TEXT("handle_id"), HandleId);
			}
		}
		else if (Op == TEXT("remove_emitter"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			bOpSuccess = UNiagaraMCPSystemLibrary::RemoveEmitter(SystemPath, Emitter);
		}
		else if (Op == TEXT("add_module"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString Stage = OpObj->GetStringField(TEXT("stage"));
			FString ModulePath = OpObj->GetStringField(TEXT("module"));
			int32 Index = OpObj->HasField(TEXT("index")) ? static_cast<int32>(OpObj->GetNumberField(TEXT("index"))) : -1;
			FString NodeGuid = UNiagaraMCPModuleLibrary::AddModule(SystemPath, Emitter, Stage, ModulePath, Index);
			bOpSuccess = !NodeGuid.IsEmpty();
			if (bOpSuccess)
			{
				ResultObj->SetStringField(TEXT("node_guid"), NodeGuid);
			}
		}
		else if (Op == TEXT("remove_module"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString ModuleGuid = OpObj->GetStringField(TEXT("module_guid"));
			bOpSuccess = UNiagaraMCPModuleLibrary::RemoveModule(SystemPath, Emitter, ModuleGuid);
		}
		else if (Op == TEXT("set_module_input"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString ModuleName = OpObj->GetStringField(TEXT("module_name"));
			FString InputName = OpObj->GetStringField(TEXT("input"));
			FString ValueStr = JsonValueToString(OpObj->TryGetField(TEXT("value")));
			bOpSuccess = UNiagaraMCPModuleLibrary::SetModuleInputValue(SystemPath, Emitter, ModuleName, InputName, ValueStr);
		}
		else if (Op == TEXT("set_module_binding"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString ModuleName = OpObj->GetStringField(TEXT("module_name"));
			FString InputName = OpObj->GetStringField(TEXT("input"));
			FString Binding = OpObj->GetStringField(TEXT("binding"));
			bOpSuccess = UNiagaraMCPModuleLibrary::SetModuleInputBinding(SystemPath, Emitter, ModuleName, InputName, Binding);
		}
		else if (Op == TEXT("set_emitter_property"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString PropName = OpObj->GetStringField(TEXT("property"));
			FString ValueStr = JsonValueToString(OpObj->TryGetField(TEXT("value")));
			bOpSuccess = UNiagaraMCPSystemLibrary::SetEmitterProperty(SystemPath, Emitter, PropName, ValueStr);
		}
		else if (Op == TEXT("add_renderer"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString RendererClass = OpObj->GetStringField(TEXT("class"));
			int32 NewIdx = UNiagaraMCPRendererLibrary::AddRenderer(SystemPath, Emitter, RendererClass);
			bOpSuccess = (NewIdx >= 0);
			if (bOpSuccess)
			{
				ResultObj->SetNumberField(TEXT("renderer_index"), NewIdx);
			}
		}
		else if (Op == TEXT("remove_renderer"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			int32 RendererIdx = static_cast<int32>(OpObj->GetNumberField(TEXT("renderer_index")));
			bOpSuccess = UNiagaraMCPRendererLibrary::RemoveRenderer(SystemPath, Emitter, RendererIdx);
		}
		else if (Op == TEXT("set_renderer_material"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			int32 RendererIdx = static_cast<int32>(OpObj->GetNumberField(TEXT("renderer_index")));
			FString Material = OpObj->GetStringField(TEXT("material"));
			bOpSuccess = UNiagaraMCPRendererLibrary::SetRendererMaterial(SystemPath, Emitter, RendererIdx, Material);
		}
		else if (Op == TEXT("set_renderer_property"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			int32 RendererIdx = static_cast<int32>(OpObj->GetNumberField(TEXT("renderer_index")));
			FString PropName = OpObj->GetStringField(TEXT("property"));
			FString ValueStr = JsonValueToString(OpObj->TryGetField(TEXT("value")));
			bOpSuccess = UNiagaraMCPRendererLibrary::SetRendererProperty(SystemPath, Emitter, RendererIdx, PropName, ValueStr);
		}
		else if (Op == TEXT("add_user_param"))
		{
			FString ParamName = OpObj->GetStringField(TEXT("name"));
			FString TypeName = OpObj->GetStringField(TEXT("type"));
			FString DefaultVal = JsonValueToString(OpObj->TryGetField(TEXT("default")));
			bOpSuccess = UNiagaraMCPParameterLibrary::AddUserParameter(SystemPath, ParamName, TypeName, DefaultVal);
		}
		else if (Op == TEXT("set_module_enabled"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString ModuleGuid = OpObj->GetStringField(TEXT("module_guid"));
			bool bEnabled = OpObj->GetBoolField(TEXT("enabled"));
			bOpSuccess = UNiagaraMCPModuleLibrary::SetModuleEnabled(SystemPath, Emitter, ModuleGuid, bEnabled);
		}
		else if (Op == TEXT("move_module"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			FString ModuleGuid = OpObj->GetStringField(TEXT("module_guid"));
			int32 NewIndex = static_cast<int32>(OpObj->GetNumberField(TEXT("new_index")));
			bOpSuccess = UNiagaraMCPModuleLibrary::MoveModule(SystemPath, Emitter, ModuleGuid, NewIndex);
		}
		else if (Op == TEXT("set_emitter_enabled"))
		{
			FString Emitter = OpObj->GetStringField(TEXT("emitter"));
			bool bEnabled = OpObj->GetBoolField(TEXT("enabled"));
			bOpSuccess = UNiagaraMCPSystemLibrary::SetEmitterEnabled(SystemPath, Emitter, bEnabled);
		}
		else
		{
			ResultObj->SetStringField(TEXT("error"), FString::Printf(TEXT("Unknown operation: %s"), *Op));
		}

		ResultObj->SetBoolField(TEXT("success"), bOpSuccess);
		ResultsArray.Add(MakeShared<FJsonValueObject>(ResultObj));

		if (bOpSuccess)
		{
			SuccessCount++;
		}
		else
		{
			FailCount++;
		}
	}

	GEditor->EndTransaction();

	// Request compile once after all operations
	System->RequestCompile(false);

	// Build final result
	TSharedRef<FJsonObject> FinalResult = MakeShared<FJsonObject>();
	FinalResult->SetBoolField(TEXT("success"), FailCount == 0);
	FinalResult->SetNumberField(TEXT("total_operations"), Operations.Num());
	FinalResult->SetNumberField(TEXT("succeeded"), SuccessCount);
	FinalResult->SetNumberField(TEXT("failed"), FailCount);
	FinalResult->SetArrayField(TEXT("results"), ResultsArray);

	UE_LOG(LogNiagaraMCPBatch, Log, TEXT("BatchExecute: %d/%d operations succeeded on system '%s'"),
		SuccessCount, Operations.Num(), *SystemPath);

	return BatchJsonToString(FinalResult);
}

// ─────────────────────────────────────────────────────────────────────────────
// CreateSystemFromSpec
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPBatchLibrary::CreateSystemFromSpec(const FString& SpecJson)
{
	// Parse the spec
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(SpecJson);
	TSharedPtr<FJsonObject> Spec;
	if (!FJsonSerializer::Deserialize(Reader, Spec) || !Spec.IsValid())
	{
		TSharedRef<FJsonObject> ErrorObj = MakeShared<FJsonObject>();
		ErrorObj->SetBoolField(TEXT("success"), false);
		ErrorObj->SetStringField(TEXT("error"), TEXT("Failed to parse spec JSON"));
		return BatchJsonToString(ErrorObj);
	}

	FString SavePath = Spec->GetStringField(TEXT("save_path"));
	FString TemplatePath = Spec->HasField(TEXT("template")) ? Spec->GetStringField(TEXT("template")) : FString();

	if (SavePath.IsEmpty())
	{
		TSharedRef<FJsonObject> ErrorObj = MakeShared<FJsonObject>();
		ErrorObj->SetBoolField(TEXT("success"), false);
		ErrorObj->SetStringField(TEXT("error"), TEXT("save_path is required"));
		return BatchJsonToString(ErrorObj);
	}

	// Step 1: Create the system
	FString SystemPath = UNiagaraMCPSystemLibrary::CreateNiagaraSystem(SavePath, TemplatePath);
	if (SystemPath.IsEmpty())
	{
		TSharedRef<FJsonObject> ErrorObj = MakeShared<FJsonObject>();
		ErrorObj->SetBoolField(TEXT("success"), false);
		ErrorObj->SetStringField(TEXT("error"), TEXT("Failed to create Niagara system"));
		return BatchJsonToString(ErrorObj);
	}

	TSharedRef<FJsonObject> FinalResult = MakeShared<FJsonObject>();
	FinalResult->SetStringField(TEXT("system_path"), SystemPath);

	TArray<TSharedPtr<FJsonValue>> StepResults;
	int32 FailCount = 0;

	// Step 2: Add user parameters (before emitters, so bindings can reference them)
	if (Spec->HasField(TEXT("user_parameters")))
	{
		const TArray<TSharedPtr<FJsonValue>>& UserParams = Spec->GetArrayField(TEXT("user_parameters"));
		for (const TSharedPtr<FJsonValue>& ParamVal : UserParams)
		{
			TSharedPtr<FJsonObject> ParamObj = ParamVal->AsObject();
			if (!ParamObj.IsValid())
			{
				continue;
			}

			FString ParamName = ParamObj->GetStringField(TEXT("name"));
			FString TypeName = ParamObj->GetStringField(TEXT("type"));
			FString DefaultVal = JsonValueToString(ParamObj->TryGetField(TEXT("default")));

			bool bOk = UNiagaraMCPParameterLibrary::AddUserParameter(SystemPath, ParamName, TypeName, DefaultVal);

			TSharedRef<FJsonObject> StepObj = MakeShared<FJsonObject>();
			StepObj->SetStringField(TEXT("step"), TEXT("add_user_param"));
			StepObj->SetStringField(TEXT("name"), ParamName);
			StepObj->SetBoolField(TEXT("success"), bOk);
			StepResults.Add(MakeShared<FJsonValueObject>(StepObj));

			if (!bOk)
			{
				FailCount++;
			}
		}
	}

	// Step 3: Add emitters with their modules and renderers
	if (Spec->HasField(TEXT("emitters")))
	{
		const TArray<TSharedPtr<FJsonValue>>& Emitters = Spec->GetArrayField(TEXT("emitters"));
		for (const TSharedPtr<FJsonValue>& EmitterVal : Emitters)
		{
			TSharedPtr<FJsonObject> EmitterObj = EmitterVal->AsObject();
			if (!EmitterObj.IsValid())
			{
				continue;
			}

			FString EmitterAsset = EmitterObj->GetStringField(TEXT("asset"));
			FString EmitterName = EmitterObj->HasField(TEXT("name")) ? EmitterObj->GetStringField(TEXT("name")) : FString();

			// Add the emitter
			FString HandleId = UNiagaraMCPSystemLibrary::AddEmitter(SystemPath, EmitterAsset, EmitterName);
			FString EmitterId = HandleId.IsEmpty() ? EmitterName : HandleId;

			TSharedRef<FJsonObject> EmitterStepObj = MakeShared<FJsonObject>();
			EmitterStepObj->SetStringField(TEXT("step"), TEXT("add_emitter"));
			EmitterStepObj->SetStringField(TEXT("name"), EmitterName);
			EmitterStepObj->SetStringField(TEXT("handle_id"), HandleId);
			EmitterStepObj->SetBoolField(TEXT("success"), !HandleId.IsEmpty());
			StepResults.Add(MakeShared<FJsonValueObject>(EmitterStepObj));

			if (HandleId.IsEmpty())
			{
				FailCount++;
				continue; // Skip further setup for this emitter
			}

			// Set emitter properties
			if (EmitterObj->HasField(TEXT("properties")))
			{
				TSharedPtr<FJsonObject> Props = EmitterObj->GetObjectField(TEXT("properties"));
				for (auto& Pair : Props->Values)
				{
					FString ValueStr = JsonValueToString(Pair.Value);
					bool bOk = UNiagaraMCPSystemLibrary::SetEmitterProperty(SystemPath, EmitterId, Pair.Key, ValueStr);

					TSharedRef<FJsonObject> PropStep = MakeShared<FJsonObject>();
					PropStep->SetStringField(TEXT("step"), TEXT("set_emitter_property"));
					PropStep->SetStringField(TEXT("emitter"), EmitterName);
					PropStep->SetStringField(TEXT("property"), Pair.Key);
					PropStep->SetBoolField(TEXT("success"), bOk);
					StepResults.Add(MakeShared<FJsonValueObject>(PropStep));

					if (!bOk)
					{
						FailCount++;
					}
				}
			}

			// Add modules
			if (EmitterObj->HasField(TEXT("modules")))
			{
				const TArray<TSharedPtr<FJsonValue>>& Modules = EmitterObj->GetArrayField(TEXT("modules"));
				for (int32 ModIdx = 0; ModIdx < Modules.Num(); ++ModIdx)
				{
					TSharedPtr<FJsonObject> ModObj = Modules[ModIdx]->AsObject();
					if (!ModObj.IsValid())
					{
						continue;
					}

					FString Stage = ModObj->GetStringField(TEXT("stage"));
					FString ScriptPath = ModObj->GetStringField(TEXT("script"));
					int32 Index = ModObj->HasField(TEXT("index")) ? static_cast<int32>(ModObj->GetNumberField(TEXT("index"))) : ModIdx;

					FString NodeGuid = UNiagaraMCPModuleLibrary::AddModule(SystemPath, EmitterId, Stage, ScriptPath, Index);

					TSharedRef<FJsonObject> ModStep = MakeShared<FJsonObject>();
					ModStep->SetStringField(TEXT("step"), TEXT("add_module"));
					ModStep->SetStringField(TEXT("emitter"), EmitterName);
					ModStep->SetStringField(TEXT("script"), ScriptPath);
					ModStep->SetStringField(TEXT("node_guid"), NodeGuid);
					ModStep->SetBoolField(TEXT("success"), !NodeGuid.IsEmpty());
					StepResults.Add(MakeShared<FJsonValueObject>(ModStep));

					if (NodeGuid.IsEmpty())
					{
						FailCount++;
						continue;
					}

					// Set module inputs
					if (ModObj->HasField(TEXT("inputs")))
					{
						TSharedPtr<FJsonObject> Inputs = ModObj->GetObjectField(TEXT("inputs"));
						for (auto& InputPair : Inputs->Values)
						{
							FString InputValueStr = JsonValueToString(InputPair.Value);
							bool bOk = UNiagaraMCPModuleLibrary::SetModuleInputValue(
								SystemPath, EmitterId, NodeGuid, InputPair.Key, InputValueStr);

							if (!bOk)
							{
								FailCount++;
								UE_LOG(LogNiagaraMCPBatch, Warning,
									TEXT("CreateSystemFromSpec: failed to set input '%s' on module '%s'"),
									*InputPair.Key, *ScriptPath);
							}
						}
					}

					// Set module bindings
					if (ModObj->HasField(TEXT("bindings")))
					{
						TSharedPtr<FJsonObject> Bindings = ModObj->GetObjectField(TEXT("bindings"));
						for (auto& BindPair : Bindings->Values)
						{
							FString BindPath = BindPair.Value->AsString();
							bool bOk = UNiagaraMCPModuleLibrary::SetModuleInputBinding(
								SystemPath, EmitterId, NodeGuid, BindPair.Key, BindPath);

							if (!bOk)
							{
								FailCount++;
							}
						}
					}
				}
			}

			// Add renderers
			if (EmitterObj->HasField(TEXT("renderers")))
			{
				const TArray<TSharedPtr<FJsonValue>>& Renderers = EmitterObj->GetArrayField(TEXT("renderers"));
				for (const TSharedPtr<FJsonValue>& RenderVal : Renderers)
				{
					TSharedPtr<FJsonObject> RenderObj = RenderVal->AsObject();
					if (!RenderObj.IsValid())
					{
						continue;
					}

					FString RendererClass = RenderObj->GetStringField(TEXT("class"));
					int32 NewIdx = UNiagaraMCPRendererLibrary::AddRenderer(SystemPath, EmitterId, RendererClass);

					TSharedRef<FJsonObject> RenderStep = MakeShared<FJsonObject>();
					RenderStep->SetStringField(TEXT("step"), TEXT("add_renderer"));
					RenderStep->SetStringField(TEXT("emitter"), EmitterName);
					RenderStep->SetStringField(TEXT("class"), RendererClass);
					RenderStep->SetNumberField(TEXT("renderer_index"), NewIdx);
					RenderStep->SetBoolField(TEXT("success"), NewIdx >= 0);
					StepResults.Add(MakeShared<FJsonValueObject>(RenderStep));

					if (NewIdx < 0)
					{
						FailCount++;
						continue;
					}

					// Set material if specified
					if (RenderObj->HasField(TEXT("material")))
					{
						FString MaterialPath = RenderObj->GetStringField(TEXT("material"));
						bool bOk = UNiagaraMCPRendererLibrary::SetRendererMaterial(
							SystemPath, EmitterId, NewIdx, MaterialPath);
						if (!bOk)
						{
							FailCount++;
						}
					}

					// Set renderer properties if specified
					if (RenderObj->HasField(TEXT("properties")))
					{
						TSharedPtr<FJsonObject> RenderProps = RenderObj->GetObjectField(TEXT("properties"));
						for (auto& RPair : RenderProps->Values)
						{
							FString RValueStr = JsonValueToString(RPair.Value);
							bool bOk = UNiagaraMCPRendererLibrary::SetRendererProperty(
								SystemPath, EmitterId, NewIdx, RPair.Key, RValueStr);
							if (!bOk)
							{
								FailCount++;
							}
						}
					}
				}
			}
		}
	}

	// Request final compile
	UNiagaraMCPSystemLibrary::RequestCompile(SystemPath);

	FinalResult->SetBoolField(TEXT("success"), FailCount == 0);
	FinalResult->SetNumberField(TEXT("failed_steps"), FailCount);
	FinalResult->SetArrayField(TEXT("steps"), StepResults);

	UE_LOG(LogNiagaraMCPBatch, Log, TEXT("CreateSystemFromSpec: created system at '%s' with %d failures"),
		*SystemPath, FailCount);

	return BatchJsonToString(FinalResult);
}
