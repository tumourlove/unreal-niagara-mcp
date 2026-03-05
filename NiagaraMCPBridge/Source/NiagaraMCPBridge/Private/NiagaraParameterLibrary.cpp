// Copyright NiagaraMCP. All Rights Reserved.

#include "NiagaraParameterLibrary.h"
#include "NiagaraSystemLibrary.h"
#include "NiagaraModuleLibrary.h"

#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraParameterStore.h"
#include "NiagaraConstants.h"
#include "NiagaraTypes.h"
#include "NiagaraScript.h"
#include "NiagaraScriptSource.h"
#include "NiagaraGraph.h"
#include "NiagaraNodeOutput.h"
#include "NiagaraNodeFunctionCall.h"
#include "ViewModels/Stack/NiagaraStackGraphUtilities.h"

#include "Editor.h"

#include "Dom/JsonObject.h"
#include "Dom/JsonValue.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/JsonWriter.h"

DEFINE_LOG_CATEGORY_STATIC(LogNiagaraMCPParam, Log, All);

// ─────────────────────────────────────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────────────────────────────────────

FNiagaraTypeDefinition UNiagaraMCPParameterLibrary::ResolveNiagaraType(const FString& TypeName)
{
	FString Lower = TypeName.ToLower();

	if (Lower == TEXT("float"))
		return FNiagaraTypeDefinition::GetFloatDef();
	if (Lower == TEXT("int") || Lower == TEXT("int32"))
		return FNiagaraTypeDefinition::GetIntDef();
	if (Lower == TEXT("bool"))
		return FNiagaraTypeDefinition::GetBoolDef();
	if (Lower == TEXT("vec2") || Lower == TEXT("vector2d") || Lower == TEXT("vector2"))
		return FNiagaraTypeDefinition::GetVec2Def();
	if (Lower == TEXT("vec3") || Lower == TEXT("vector") || Lower == TEXT("vector3"))
		return FNiagaraTypeDefinition::GetVec3Def();
	if (Lower == TEXT("vec4") || Lower == TEXT("vector4"))
		return FNiagaraTypeDefinition::GetVec4Def();
	if (Lower == TEXT("color") || Lower == TEXT("linearcolor"))
		return FNiagaraTypeDefinition::GetColorDef();
	if (Lower == TEXT("position"))
		return FNiagaraTypeDefinition::GetPositionDef();
	if (Lower == TEXT("quat") || Lower == TEXT("quaternion"))
		return FNiagaraTypeDefinition::GetQuatDef();
	if (Lower == TEXT("matrix") || Lower == TEXT("matrix4"))
		return FNiagaraTypeDefinition::GetMatrix4Def();

	UE_LOG(LogNiagaraMCPParam, Warning, TEXT("Unknown type '%s', defaulting to float"), *TypeName);
	return FNiagaraTypeDefinition::GetFloatDef();
}

FNiagaraVariable UNiagaraMCPParameterLibrary::MakeUserVariable(const FString& ParamName, const FNiagaraTypeDefinition& TypeDef)
{
	// Ensure the User. namespace prefix
	FString FullName = ParamName;
	if (!FullName.StartsWith(TEXT("User.")))
	{
		FullName = TEXT("User.") + FullName;
	}

	FNiagaraVariable Var(TypeDef, FName(*FullName));
	return Var;
}

FString UNiagaraMCPParameterLibrary::SerializeParameterValue(const FNiagaraVariable& Variable, const FNiagaraParameterStore& Store)
{
	const FNiagaraTypeDefinition& TypeDef = Variable.GetType();

	if (TypeDef == FNiagaraTypeDefinition::GetFloatDef())
	{
		float Value = Store.GetParameterValue<float>(Variable);
		return FString::SanitizeFloat(Value);
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetIntDef())
	{
		int32 Value = Store.GetParameterValue<int32>(Variable);
		return FString::FromInt(Value);
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetBoolDef())
	{
		// Niagara bools are stored as FNiagaraBool
		FNiagaraBool Value = Store.GetParameterValue<FNiagaraBool>(Variable);
		return Value.IsValid() && Value.GetValue() ? TEXT("true") : TEXT("false");
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetVec2Def())
	{
		FVector2f Value = Store.GetParameterValue<FVector2f>(Variable);
		TSharedRef<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetNumberField(TEXT("x"), Value.X);
		Obj->SetNumberField(TEXT("y"), Value.Y);
		FString Result;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
		FJsonSerializer::Serialize(Obj, Writer);
		return Result;
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetVec3Def() || TypeDef == FNiagaraTypeDefinition::GetPositionDef())
	{
		FVector3f Value = Store.GetParameterValue<FVector3f>(Variable);
		TSharedRef<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetNumberField(TEXT("x"), Value.X);
		Obj->SetNumberField(TEXT("y"), Value.Y);
		Obj->SetNumberField(TEXT("z"), Value.Z);
		FString Result;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
		FJsonSerializer::Serialize(Obj, Writer);
		return Result;
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetVec4Def() || TypeDef == FNiagaraTypeDefinition::GetQuatDef())
	{
		FVector4f Value = Store.GetParameterValue<FVector4f>(Variable);
		TSharedRef<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetNumberField(TEXT("x"), Value.X);
		Obj->SetNumberField(TEXT("y"), Value.Y);
		Obj->SetNumberField(TEXT("z"), Value.Z);
		Obj->SetNumberField(TEXT("w"), Value.W);
		FString Result;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
		FJsonSerializer::Serialize(Obj, Writer);
		return Result;
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetColorDef())
	{
		FLinearColor Value = Store.GetParameterValue<FLinearColor>(Variable);
		TSharedRef<FJsonObject> Obj = MakeShared<FJsonObject>();
		Obj->SetNumberField(TEXT("r"), Value.R);
		Obj->SetNumberField(TEXT("g"), Value.G);
		Obj->SetNumberField(TEXT("b"), Value.B);
		Obj->SetNumberField(TEXT("a"), Value.A);
		FString Result;
		TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
		FJsonSerializer::Serialize(Obj, Writer);
		return Result;
	}

	return TEXT("\"<unsupported type>\"");
}

// Helper: serialize JSON object to string
static FString ParamJsonToString(const TSharedRef<FJsonObject>& Obj)
{
	FString Result;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
	FJsonSerializer::Serialize(Obj, Writer);
	return Result;
}

static FString ParamJsonArrayToString(const TArray<TSharedPtr<FJsonValue>>& Arr)
{
	FString Result;
	TSharedRef<TJsonWriter<>> Writer = TJsonWriterFactory<>::Create(&Result);
	FJsonSerializer::Serialize(Arr, Writer);
	return Result;
}

// Helper: collect parameters from a store into a JSON array
static void CollectParametersFromStore(const FNiagaraParameterStore& Store, const FString& Scope,
	TArray<TSharedPtr<FJsonValue>>& OutArray)
{
	TArrayView<const FNiagaraVariableWithOffset> Variables = Store.ReadParameterVariables();
	for (const FNiagaraVariableWithOffset& VarWithOffset : Variables)
	{
		const FNiagaraVariable& Var = VarWithOffset;
		TSharedRef<FJsonObject> ParamObj = MakeShared<FJsonObject>();
		ParamObj->SetStringField(TEXT("name"), Var.GetName().ToString());
		ParamObj->SetStringField(TEXT("type"), Var.GetType().GetName());
		ParamObj->SetStringField(TEXT("scope"), Scope);

		// Try to serialize value
		FString ValueStr = UNiagaraMCPParameterLibrary::SerializeParameterValue(Var, Store);
		ParamObj->SetStringField(TEXT("value"), ValueStr);

		OutArray.Add(MakeShared<FJsonValueObject>(ParamObj));
	}
}

// ─────────────────────────────────────────────────────────────────────────────
// GetAllParameters
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPParameterLibrary::GetAllParameters(const FString& SystemPath)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	TArray<TSharedPtr<FJsonValue>> AllParams;

	// System exposed (user) parameters
	FNiagaraUserRedirectionParameterStore& UserStore = System->GetExposedParameters();
	CollectParametersFromStore(UserStore, TEXT("User"), AllParams);

	// Per-emitter parameters
	const TArray<FNiagaraEmitterHandle>& Handles = System->GetEmitterHandles();
	for (const FNiagaraEmitterHandle& Handle : Handles)
	{
		FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData();
		if (!EmitterData)
		{
			continue;
		}

		FString EmitterScope = FString::Printf(TEXT("Emitter.%s"), *Handle.GetName().ToString());

		// Collect from emitter scripts
		static const ENiagaraScriptUsage ScriptUsages[] = {
			ENiagaraScriptUsage::EmitterSpawnScript,
			ENiagaraScriptUsage::EmitterUpdateScript,
			ENiagaraScriptUsage::ParticleSpawnScript,
			ENiagaraScriptUsage::ParticleUpdateScript,
		};

		for (ENiagaraScriptUsage Usage : ScriptUsages)
		{
			UNiagaraScript* Script = EmitterData->GetScript(Usage, FGuid());
			if (Script)
			{
				const FNiagaraParameterStore& ScriptStore = Script->GetRapidIterationParameters();
				FString UsageStr = StaticEnum<ENiagaraScriptUsage>()->GetNameStringByValue(static_cast<int64>(Usage));
				FString ScopeStr = FString::Printf(TEXT("%s.%s"), *EmitterScope, *UsageStr);
				CollectParametersFromStore(ScriptStore, ScopeStr, AllParams);
			}
		}
	}

	return ParamJsonArrayToString(AllParams);
}

// ─────────────────────────────────────────────────────────────────────────────
// GetUserParameters
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPParameterLibrary::GetUserParameters(const FString& SystemPath)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	FNiagaraUserRedirectionParameterStore& UserStore = System->GetExposedParameters();

	TArray<FNiagaraVariable> UserParams;
	UserStore.GetUserParameters(UserParams);

	TArray<TSharedPtr<FJsonValue>> JsonArray;
	for (const FNiagaraVariable& Param : UserParams)
	{
		TSharedRef<FJsonObject> ParamObj = MakeShared<FJsonObject>();
		ParamObj->SetStringField(TEXT("name"), Param.GetName().ToString());
		ParamObj->SetStringField(TEXT("type"), Param.GetType().GetName());

		FString ValueStr = SerializeParameterValue(Param, UserStore);
		ParamObj->SetStringField(TEXT("value"), ValueStr);

		JsonArray.Add(MakeShared<FJsonValueObject>(ParamObj));
	}

	return ParamJsonArrayToString(JsonArray);
}

// ─────────────────────────────────────────────────────────────────────────────
// GetParameterValue
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPParameterLibrary::GetParameterValue(const FString& SystemPath, const FString& ParamName)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	FNiagaraUserRedirectionParameterStore& UserStore = System->GetExposedParameters();

	// Search the user store
	TArray<FNiagaraVariable> UserParams;
	UserStore.GetUserParameters(UserParams);

	FString SearchName = ParamName;
	if (!SearchName.StartsWith(TEXT("User.")))
	{
		SearchName = TEXT("User.") + SearchName;
	}

	for (const FNiagaraVariable& Param : UserParams)
	{
		if (Param.GetName().ToString() == SearchName || Param.GetName().ToString() == ParamName)
		{
			TSharedRef<FJsonObject> ResultObj = MakeShared<FJsonObject>();
			ResultObj->SetStringField(TEXT("name"), Param.GetName().ToString());
			ResultObj->SetStringField(TEXT("type"), Param.GetType().GetName());
			ResultObj->SetStringField(TEXT("value"), SerializeParameterValue(Param, UserStore));
			return ParamJsonToString(ResultObj);
		}
	}

	UE_LOG(LogNiagaraMCPParam, Warning, TEXT("GetParameterValue: parameter '%s' not found"), *ParamName);
	return FString();
}

// ─────────────────────────────────────────────────────────────────────────────
// GetParameterType
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPParameterLibrary::GetParameterType(const FString& TypeName)
{
	FNiagaraTypeDefinition TypeDef = ResolveNiagaraType(TypeName);

	TSharedRef<FJsonObject> TypeObj = MakeShared<FJsonObject>();
	TypeObj->SetStringField(TEXT("name"), TypeDef.GetName());
	TypeObj->SetNumberField(TEXT("size"), TypeDef.GetSize());
	TypeObj->SetBoolField(TEXT("is_float_primitive"), TypeDef == FNiagaraTypeDefinition::GetFloatDef());
	TypeObj->SetBoolField(TEXT("is_data_interface"), TypeDef.IsDataInterface());
	TypeObj->SetBoolField(TEXT("is_enum"), TypeDef.IsEnum());
	TypeObj->SetBoolField(TEXT("is_valid"), TypeDef.IsValid());

	if (TypeDef.GetStruct())
	{
		TypeObj->SetStringField(TEXT("struct_name"), TypeDef.GetStruct()->GetName());
	}

	return ParamJsonToString(TypeObj);
}

// ─────────────────────────────────────────────────────────────────────────────
// TraceParameterBinding
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPParameterLibrary::TraceParameterBinding(const FString& SystemPath, const FString& ParamName)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	FString SearchName = ParamName;
	if (!SearchName.StartsWith(TEXT("User.")))
	{
		SearchName = TEXT("User.") + SearchName;
	}

	TSharedRef<FJsonObject> TraceObj = MakeShared<FJsonObject>();
	TraceObj->SetStringField(TEXT("parameter"), SearchName);

	// Check if parameter exists in user store
	FNiagaraUserRedirectionParameterStore& UserStore = System->GetExposedParameters();
	TArray<FNiagaraVariable> UserParams;
	UserStore.GetUserParameters(UserParams);

	bool bFound = false;
	FNiagaraTypeDefinition ParamType;
	for (const FNiagaraVariable& Param : UserParams)
	{
		if (Param.GetName().ToString() == SearchName)
		{
			bFound = true;
			ParamType = Param.GetType();
			TraceObj->SetStringField(TEXT("type"), Param.GetType().GetName());
			TraceObj->SetStringField(TEXT("source"), TEXT("ExposedParameters"));
			TraceObj->SetStringField(TEXT("value"), SerializeParameterValue(Param, UserStore));
			break;
		}
	}

	if (!bFound)
	{
		TraceObj->SetStringField(TEXT("error"), TEXT("Parameter not found in user store"));
		return ParamJsonToString(TraceObj);
	}

	// Trace through emitters to find modules that reference this parameter
	TArray<TSharedPtr<FJsonValue>> Bindings;
	const TArray<FNiagaraEmitterHandle>& Handles = System->GetEmitterHandles();

	for (const FNiagaraEmitterHandle& Handle : Handles)
	{
		FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData();
		if (!EmitterData)
		{
			continue;
		}

		FString EmitterName = Handle.GetName().ToString();

		// Search across all script usages
		static const ENiagaraScriptUsage AllUsages[] = {
			ENiagaraScriptUsage::EmitterSpawnScript,
			ENiagaraScriptUsage::EmitterUpdateScript,
			ENiagaraScriptUsage::ParticleSpawnScript,
			ENiagaraScriptUsage::ParticleUpdateScript,
		};

		for (ENiagaraScriptUsage Usage : AllUsages)
		{
			UNiagaraNodeOutput* OutputNode = UNiagaraMCPModuleLibrary::FindOutputNode(System, Handle.GetId().ToString(), Usage);
			if (!OutputNode)
			{
				continue;
			}

			TArray<UNiagaraNodeFunctionCall*> ModuleNodes;
			FNiagaraStackGraphUtilities::GetOrderedModuleNodes(*OutputNode, ModuleNodes);

			for (UNiagaraNodeFunctionCall* ModNode : ModuleNodes)
			{
				if (!ModNode)
				{
					continue;
				}

				// Check each input of this module for bindings to our parameter
				for (UEdGraphPin* Pin : ModNode->Pins)
				{
					if (Pin->Direction != EGPD_Input)
					{
						continue;
					}

					// Check linked pins for our parameter
					for (UEdGraphPin* LinkedPin : Pin->LinkedTo)
					{
						UEdGraphNode* LinkedNode = LinkedPin->GetOwningNode();
						if (LinkedNode)
						{
							FString LinkedName = LinkedPin->PinName.ToString();
							if (LinkedName.Contains(SearchName) || LinkedName.Contains(ParamName))
							{
								TSharedRef<FJsonObject> BindingObj = MakeShared<FJsonObject>();
								BindingObj->SetStringField(TEXT("emitter"), EmitterName);
								BindingObj->SetStringField(TEXT("module"), ModNode->GetFunctionName());
								BindingObj->SetStringField(TEXT("input_pin"), Pin->PinName.ToString());
								BindingObj->SetStringField(TEXT("usage"),
									StaticEnum<ENiagaraScriptUsage>()->GetNameStringByValue(static_cast<int64>(Usage)));
								Bindings.Add(MakeShared<FJsonValueObject>(BindingObj));
							}
						}
					}
				}
			}
		}
	}

	TraceObj->SetArrayField(TEXT("bindings"), Bindings);
	return ParamJsonToString(TraceObj);
}

// ─────────────────────────────────────────────────────────────────────────────
// AddUserParameter
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPParameterLibrary::AddUserParameter(const FString& SystemPath, const FString& ParamName,
	const FString& TypeName, const FString& DefaultValueJson)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	FNiagaraTypeDefinition TypeDef = ResolveNiagaraType(TypeName);
	FNiagaraVariable NewVar = MakeUserVariable(ParamName, TypeDef);

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "AddUserParam", "Add User Parameter"));
	System->Modify();

	FNiagaraUserRedirectionParameterStore& UserStore = System->GetExposedParameters();
	UserStore.AddParameter(NewVar, true, false);

	// Set default value if provided
	if (!DefaultValueJson.IsEmpty())
	{
		TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(DefaultValueJson);
		TSharedPtr<FJsonValue> JsonValue;
		if (FJsonSerializer::Deserialize(Reader, JsonValue) && JsonValue.IsValid())
		{
			if (TypeDef == FNiagaraTypeDefinition::GetFloatDef())
			{
				float Val = static_cast<float>(JsonValue->AsNumber());
				UserStore.SetParameterValue<float>(Val, NewVar, true);
			}
			else if (TypeDef == FNiagaraTypeDefinition::GetIntDef())
			{
				int32 Val = static_cast<int32>(JsonValue->AsNumber());
				UserStore.SetParameterValue<int32>(Val, NewVar, true);
			}
			else if (TypeDef == FNiagaraTypeDefinition::GetBoolDef())
			{
				FNiagaraBool Val;
				Val.SetValue(JsonValue->AsBool());
				UserStore.SetParameterValue<FNiagaraBool>(Val, NewVar, true);
			}
			else if (TypeDef == FNiagaraTypeDefinition::GetVec2Def())
			{
				TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
				if (Obj)
				{
					FVector2f Val(
						static_cast<float>(Obj->GetNumberField(TEXT("x"))),
						static_cast<float>(Obj->GetNumberField(TEXT("y")))
					);
					UserStore.SetParameterValue<FVector2f>(Val, NewVar, true);
				}
			}
			else if (TypeDef == FNiagaraTypeDefinition::GetVec3Def() || TypeDef == FNiagaraTypeDefinition::GetPositionDef())
			{
				TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
				if (Obj)
				{
					FVector3f Val(
						static_cast<float>(Obj->GetNumberField(TEXT("x"))),
						static_cast<float>(Obj->GetNumberField(TEXT("y"))),
						static_cast<float>(Obj->GetNumberField(TEXT("z")))
					);
					UserStore.SetParameterValue<FVector3f>(Val, NewVar, true);
				}
			}
			else if (TypeDef == FNiagaraTypeDefinition::GetVec4Def() || TypeDef == FNiagaraTypeDefinition::GetQuatDef())
			{
				TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
				if (Obj)
				{
					FVector4f Val(
						static_cast<float>(Obj->GetNumberField(TEXT("x"))),
						static_cast<float>(Obj->GetNumberField(TEXT("y"))),
						static_cast<float>(Obj->GetNumberField(TEXT("z"))),
						static_cast<float>(Obj->GetNumberField(TEXT("w")))
					);
					UserStore.SetParameterValue<FVector4f>(Val, NewVar, true);
				}
			}
			else if (TypeDef == FNiagaraTypeDefinition::GetColorDef())
			{
				TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
				if (Obj)
				{
					FLinearColor Val(
						static_cast<float>(Obj->GetNumberField(TEXT("r"))),
						static_cast<float>(Obj->GetNumberField(TEXT("g"))),
						static_cast<float>(Obj->GetNumberField(TEXT("b"))),
						Obj->HasField(TEXT("a")) ? static_cast<float>(Obj->GetNumberField(TEXT("a"))) : 1.0f
					);
					UserStore.SetParameterValue<FLinearColor>(Val, NewVar, true);
				}
			}
		}
	}

	GEditor->EndTransaction();

	UE_LOG(LogNiagaraMCPParam, Log, TEXT("Added user parameter '%s' of type '%s' to system '%s'"),
		*ParamName, *TypeName, *SystemPath);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// RemoveUserParameter
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPParameterLibrary::RemoveUserParameter(const FString& SystemPath, const FString& ParamName)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	FString SearchName = ParamName;
	if (!SearchName.StartsWith(TEXT("User.")))
	{
		SearchName = TEXT("User.") + SearchName;
	}

	FNiagaraUserRedirectionParameterStore& UserStore = System->GetExposedParameters();

	// Find the parameter to get its type
	TArray<FNiagaraVariable> UserParams;
	UserStore.GetUserParameters(UserParams);

	FNiagaraVariable FoundVar;
	bool bFound = false;
	for (const FNiagaraVariable& Param : UserParams)
	{
		if (Param.GetName().ToString() == SearchName || Param.GetName().ToString() == ParamName)
		{
			FoundVar = Param;
			bFound = true;
			break;
		}
	}

	if (!bFound)
	{
		UE_LOG(LogNiagaraMCPParam, Error, TEXT("RemoveUserParameter: parameter '%s' not found"), *ParamName);
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "RemoveUserParam", "Remove User Parameter"));
	System->Modify();

	UserStore.RemoveParameter(FoundVar);

	GEditor->EndTransaction();

	UE_LOG(LogNiagaraMCPParam, Log, TEXT("Removed user parameter '%s' from system '%s'"),
		*ParamName, *SystemPath);
	return true;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetParameterDefault
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPParameterLibrary::SetParameterDefault(const FString& SystemPath, const FString& ParamName, const FString& ValueJson)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	FString SearchName = ParamName;
	if (!SearchName.StartsWith(TEXT("User.")))
	{
		SearchName = TEXT("User.") + SearchName;
	}

	FNiagaraUserRedirectionParameterStore& UserStore = System->GetExposedParameters();

	TArray<FNiagaraVariable> UserParams;
	UserStore.GetUserParameters(UserParams);

	FNiagaraVariable FoundVar;
	bool bFound = false;
	for (const FNiagaraVariable& Param : UserParams)
	{
		if (Param.GetName().ToString() == SearchName || Param.GetName().ToString() == ParamName)
		{
			FoundVar = Param;
			bFound = true;
			break;
		}
	}

	if (!bFound)
	{
		UE_LOG(LogNiagaraMCPParam, Error, TEXT("SetParameterDefault: parameter '%s' not found"), *ParamName);
		return false;
	}

	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(ValueJson);
	TSharedPtr<FJsonValue> JsonValue;
	if (!FJsonSerializer::Deserialize(Reader, JsonValue) || !JsonValue.IsValid())
	{
		UE_LOG(LogNiagaraMCPParam, Error, TEXT("SetParameterDefault: failed to parse JSON: %s"), *ValueJson);
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetParamDefault", "Set Parameter Default"));
	System->Modify();

	const FNiagaraTypeDefinition& TypeDef = FoundVar.GetType();
	bool bSuccess = false;

	if (TypeDef == FNiagaraTypeDefinition::GetFloatDef())
	{
		float Val = static_cast<float>(JsonValue->AsNumber());
		UserStore.SetParameterValue<float>(Val, FoundVar, true);
		bSuccess = true;
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetIntDef())
	{
		int32 Val = static_cast<int32>(JsonValue->AsNumber());
		UserStore.SetParameterValue<int32>(Val, FoundVar, true);
		bSuccess = true;
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetBoolDef())
	{
		FNiagaraBool Val;
		Val.SetValue(JsonValue->AsBool());
		UserStore.SetParameterValue<FNiagaraBool>(Val, FoundVar, true);
		bSuccess = true;
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetVec2Def())
	{
		TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
		if (Obj)
		{
			FVector2f Val(
				static_cast<float>(Obj->GetNumberField(TEXT("x"))),
				static_cast<float>(Obj->GetNumberField(TEXT("y")))
			);
			UserStore.SetParameterValue<FVector2f>(Val, FoundVar, true);
			bSuccess = true;
		}
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetVec3Def() || TypeDef == FNiagaraTypeDefinition::GetPositionDef())
	{
		TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
		if (Obj)
		{
			FVector3f Val(
				static_cast<float>(Obj->GetNumberField(TEXT("x"))),
				static_cast<float>(Obj->GetNumberField(TEXT("y"))),
				static_cast<float>(Obj->GetNumberField(TEXT("z")))
			);
			UserStore.SetParameterValue<FVector3f>(Val, FoundVar, true);
			bSuccess = true;
		}
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetVec4Def() || TypeDef == FNiagaraTypeDefinition::GetQuatDef())
	{
		TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
		if (Obj)
		{
			FVector4f Val(
				static_cast<float>(Obj->GetNumberField(TEXT("x"))),
				static_cast<float>(Obj->GetNumberField(TEXT("y"))),
				static_cast<float>(Obj->GetNumberField(TEXT("z"))),
				static_cast<float>(Obj->GetNumberField(TEXT("w")))
			);
			UserStore.SetParameterValue<FVector4f>(Val, FoundVar, true);
			bSuccess = true;
		}
	}
	else if (TypeDef == FNiagaraTypeDefinition::GetColorDef())
	{
		TSharedPtr<FJsonObject> Obj = JsonValue->AsObject();
		if (Obj)
		{
			FLinearColor Val(
				static_cast<float>(Obj->GetNumberField(TEXT("r"))),
				static_cast<float>(Obj->GetNumberField(TEXT("g"))),
				static_cast<float>(Obj->GetNumberField(TEXT("b"))),
				Obj->HasField(TEXT("a")) ? static_cast<float>(Obj->GetNumberField(TEXT("a"))) : 1.0f
			);
			UserStore.SetParameterValue<FLinearColor>(Val, FoundVar, true);
			bSuccess = true;
		}
	}
	else
	{
		UE_LOG(LogNiagaraMCPParam, Error, TEXT("SetParameterDefault: unsupported type '%s'"),
			*TypeDef.GetName());
	}

	GEditor->EndTransaction();

	if (bSuccess)
	{
		UE_LOG(LogNiagaraMCPParam, Log, TEXT("Set parameter default for '%s' in system '%s'"),
			*ParamName, *SystemPath);
	}
	return bSuccess;
}

// ─────────────────────────────────────────────────────────────────────────────
// SetCurveValue
// ─────────────────────────────────────────────────────────────────────────────

bool UNiagaraMCPParameterLibrary::SetCurveValue(const FString& SystemPath, const FString& EmitterHandleId,
	const FString& ModuleName, const FString& InputName, const FString& CurveKeysJson)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return false;
	}

	// Parse curve keys JSON: [{"time": 0.0, "value": 1.0, "arrive_tangent": 0.0, "leave_tangent": 0.0}, ...]
	TSharedRef<TJsonReader<>> Reader = TJsonReaderFactory<>::Create(CurveKeysJson);
	TArray<TSharedPtr<FJsonValue>> KeysArray;
	if (!FJsonSerializer::Deserialize(Reader, KeysArray))
	{
		UE_LOG(LogNiagaraMCPParam, Error, TEXT("SetCurveValue: failed to parse curve keys JSON"));
		return false;
	}

	// Build the curve key string in Niagara's format
	// Niagara stores curves as a series of keys in the rapid iteration parameter store
	// For simplicity, we'll construct a serialized string that can be set as a pin override
	TArray<FString> KeyStrings;
	for (const TSharedPtr<FJsonValue>& KeyVal : KeysArray)
	{
		TSharedPtr<FJsonObject> KeyObj = KeyVal->AsObject();
		if (!KeyObj)
		{
			continue;
		}

		float Time = static_cast<float>(KeyObj->GetNumberField(TEXT("time")));
		float Value = static_cast<float>(KeyObj->GetNumberField(TEXT("value")));
		float ArriveTangent = KeyObj->HasField(TEXT("arrive_tangent"))
			? static_cast<float>(KeyObj->GetNumberField(TEXT("arrive_tangent")))
			: 0.0f;
		float LeaveTangent = KeyObj->HasField(TEXT("leave_tangent"))
			? static_cast<float>(KeyObj->GetNumberField(TEXT("leave_tangent")))
			: 0.0f;

		KeyStrings.Add(FString::Printf(TEXT("(Time=%f,Value=%f,ArriveTangent=%f,LeaveTangent=%f)"),
			Time, Value, ArriveTangent, LeaveTangent));
	}

	FString CurveString = TEXT("(") + FString::Join(KeyStrings, TEXT(",")) + TEXT(")");

	// Find the module node and set the input via the module library
	UNiagaraNodeFunctionCall* ModuleNode = UNiagaraMCPModuleLibrary::FindModuleNode(System, EmitterHandleId, ModuleName);
	if (!ModuleNode)
	{
		UE_LOG(LogNiagaraMCPParam, Error, TEXT("SetCurveValue: module '%s' not found"), *ModuleName);
		return false;
	}

	GEditor->BeginTransaction(NSLOCTEXT("NiagaraMCP", "SetCurveValue", "Set Curve Value"));
	System->Modify();

	FNiagaraParameterHandle ParamHandle(FName(*InputName));
	UEdGraphPin* OverridePin = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(
		*ModuleNode, ParamHandle);

	if (OverridePin)
	{
		OverridePin->DefaultValue = CurveString;
	}
	else
	{
		UE_LOG(LogNiagaraMCPParam, Error, TEXT("SetCurveValue: could not get/create override pin for '%s'"), *InputName);
		GEditor->EndTransaction();
		return false;
	}

	GEditor->EndTransaction();

	System->RequestCompile(false);

	UE_LOG(LogNiagaraMCPParam, Log, TEXT("Set curve with %d keys on input '%s' of module '%s'"),
		KeysArray.Num(), *InputName, *ModuleName);
	return true;
}
