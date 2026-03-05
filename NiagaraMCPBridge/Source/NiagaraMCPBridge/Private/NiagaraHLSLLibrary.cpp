// Copyright NiagaraMCP. All Rights Reserved.

#include "NiagaraHLSLLibrary.h"
#include "NiagaraSystemLibrary.h"

#include "NiagaraSystem.h"
#include "NiagaraEmitter.h"
#include "NiagaraEmitterHandle.h"
#include "NiagaraScript.h"
#include "NiagaraCommon.h"

DEFINE_LOG_CATEGORY_STATIC(LogNiagaraMCPHLSL, Log, All);

// ─────────────────────────────────────────────────────────────────────────────
// GetCompiledGPUHLSL
// ─────────────────────────────────────────────────────────────────────────────

FString UNiagaraMCPHLSLLibrary::GetCompiledGPUHLSL(const FString& SystemPath, const FString& EmitterHandleId)
{
	UNiagaraSystem* System = UNiagaraMCPSystemLibrary::LoadSystem(SystemPath);
	if (!System)
	{
		return FString();
	}

	int32 EmitterIndex = UNiagaraMCPSystemLibrary::FindEmitterHandleIndex(System, EmitterHandleId);
	if (EmitterIndex == INDEX_NONE)
	{
		UE_LOG(LogNiagaraMCPHLSL, Error, TEXT("GetCompiledGPUHLSL: emitter handle '%s' not found"), *EmitterHandleId);
		return FString();
	}

	const FNiagaraEmitterHandle& Handle = System->GetEmitterHandles()[EmitterIndex];
	FVersionedNiagaraEmitterData* EmitterData = Handle.GetEmitterData();
	if (!EmitterData)
	{
		UE_LOG(LogNiagaraMCPHLSL, Error, TEXT("GetCompiledGPUHLSL: no emitter data for handle '%s'"), *EmitterHandleId);
		return FString();
	}

	// Check if the emitter is set to GPU simulation
	if (EmitterData->SimTarget != ENiagaraSimTarget::GPUComputeSim)
	{
		UE_LOG(LogNiagaraMCPHLSL, Warning, TEXT("GetCompiledGPUHLSL: emitter '%s' is not set to GPU simulation target"),
			*EmitterHandleId);
		return FString(TEXT("ERROR: Emitter is not configured for GPU simulation."));
	}

	// Get the GPU compute script
	UNiagaraScript* GPUScript = EmitterData->GetGPUComputeScript();
	if (!GPUScript)
	{
		UE_LOG(LogNiagaraMCPHLSL, Error, TEXT("GetCompiledGPUHLSL: no GPU compute script found for emitter '%s'"),
			*EmitterHandleId);
		return FString();
	}

	// Ensure the system is compiled
	if (System->HasOutstandingCompilationRequests())
	{
		UE_LOG(LogNiagaraMCPHLSL, Warning, TEXT("GetCompiledGPUHLSL: system has outstanding compilation requests, results may be stale"));
	}

	FString HLSL;

#if WITH_EDITORONLY_DATA
	const FNiagaraVMExecutableData& ExeData = GPUScript->GetVMExecutableData();
	if (!ExeData.LastHlslTranslationGPU.IsEmpty())
	{
		HLSL = ExeData.LastHlslTranslationGPU;
	}
	else if (!ExeData.LastHlslTranslation.IsEmpty())
	{
		UE_LOG(LogNiagaraMCPHLSL, Warning, TEXT("GPU HLSL not available, returning VM HLSL"));
		HLSL = ExeData.LastHlslTranslation;
	}
	else if (!ExeData.LastAssemblyTranslation.IsEmpty())
	{
		UE_LOG(LogNiagaraMCPHLSL, Warning, TEXT("HLSL not available, returning assembly"));
		HLSL = ExeData.LastAssemblyTranslation;
	}
	else
	{
		UE_LOG(LogNiagaraMCPHLSL, Error, TEXT("No compiled HLSL available. Call RequestCompile first."));
		return FString(TEXT("ERROR: No compiled HLSL available."));
	}
#else
	return FString(TEXT("ERROR: HLSL only available in editor builds."));
#endif

	UE_LOG(LogNiagaraMCPHLSL, Log, TEXT("Retrieved %d characters of GPU HLSL for emitter '%s'"),
		HLSL.Len(), *EmitterHandleId);
	return HLSL;
}
