// Copyright NiagaraMCP. All Rights Reserved.

#include "Modules/ModuleManager.h"

class FNiagaraMCPBridgeModule : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		UE_LOG(LogTemp, Log, TEXT("NiagaraMCPBridge: Module loaded."));
	}

	virtual void ShutdownModule() override
	{
		UE_LOG(LogTemp, Log, TEXT("NiagaraMCPBridge: Module unloaded."));
	}
};

IMPLEMENT_MODULE(FNiagaraMCPBridgeModule, NiagaraMCPBridge)
