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

	// Access the compiled data to extract the HLSL source
	const TArray<uint8>& ByteCode = GPUScript->GetScriptByteCode();
	if (ByteCode.Num() == 0)
	{
		UE_LOG(LogNiagaraMCPHLSL, Warning, TEXT("GetCompiledGPUHLSL: no compiled bytecode available, trying HLSL output"));
	}

	// The compiled HLSL is stored in the script's last compile status / generated HLSL
	// Access via the VM executable data or the generated HLSL debug output
	FString HLSL;

	// Try to get HLSL from the compile results
	const FNiagaraVMExecutableData& ExeData = GPUScript->GetVMExecutableData();
	if (!ExeData.LastHlslTranslation.IsEmpty())
	{
		HLSL = ExeData.LastHlslTranslation;
	}
	else if (!ExeData.LastAssemblyTranslation.IsEmpty())
	{
		// Fallback: return assembly if HLSL not available
		UE_LOG(LogNiagaraMCPHLSL, Warning, TEXT("GetCompiledGPUHLSL: HLSL not available, returning assembly translation"));
		HLSL = ExeData.LastAssemblyTranslation;
	}
	else
	{
		UE_LOG(LogNiagaraMCPHLSL, Error, TEXT("GetCompiledGPUHLSL: no compiled HLSL or assembly available. Ensure the system is compiled."));
		return FString(TEXT("ERROR: No compiled HLSL available. Call RequestCompile first."));
	}

	UE_LOG(LogNiagaraMCPHLSL, Log, TEXT("Retrieved %d characters of GPU HLSL for emitter '%s'"),
		HLSL.Len(), *EmitterHandleId);
	return HLSL;
}
