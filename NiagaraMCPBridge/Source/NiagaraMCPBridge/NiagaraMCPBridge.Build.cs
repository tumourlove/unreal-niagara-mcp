// Copyright NiagaraMCP. All Rights Reserved.

using UnrealBuildTool;

public class NiagaraMCPBridge : ModuleRules
{
	public NiagaraMCPBridge(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = ModuleRules.PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine",
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"UnrealEd",
			"Niagara",
			"NiagaraCore",
			"NiagaraEditor",
			"Json",
			"JsonUtilities",
			"AssetTools",
			"Slate",
			"SlateCore",
			"EditorFramework",
		});
	}
}
