from pathlib import Path
import shutil

FILES = {
    "clean_examples/project_aurora/characters/chr_knight/geo/Chr_KnightBody_v001.fbx": "Placeholder FBX asset: knight body\n",
    "clean_examples/project_aurora/characters/chr_knight/geo/Chr_KnightHelmet_v001.fbx": "Placeholder FBX asset: knight helmet\n",
    "clean_examples/project_aurora/characters/chr_knight/textures/T_Chr_KnightBody_D_v001.png": "Placeholder texture: knight body diffuse\n",
    "clean_examples/project_aurora/characters/chr_knight/textures/T_Chr_KnightBody_N_v001.png": "Placeholder texture: knight body normal\n",
    "clean_examples/project_aurora/characters/chr_knight/textures/T_Chr_KnightHelmet_D_v001.png": "Placeholder texture: knight helmet diffuse\n",
    "clean_examples/project_aurora/characters/chr_knight/materials/M_Chr_KnightBody_v001.json": "{\n  \"material\": \"chr_knight_body\",\n  \"version\": \"v001\"\n}\n",
    "clean_examples/project_aurora/characters/chr_knight/docs/Chr_KnightNotes_v001.txt": "Knight asset notes. Clean example.\n",
    "clean_examples/project_aurora/props/prp_lantern/geo/Prp_Lantern_v002.fbx": "Placeholder FBX asset: lantern\n",
    "clean_examples/project_aurora/props/prp_lantern/textures/T_Prp_Lantern_D_v002.png": "Placeholder texture: lantern diffuse\n",
    "clean_examples/project_aurora/props/prp_lantern/textures/T_Prp_Lantern_E_v001.png": "Placeholder texture: lantern emissive\n",
    "clean_examples/project_aurora/props/prp_lantern/materials/M_Prp_Lantern_v001.json": "{\n  \"material\": \"prp_lantern\",\n  \"version\": \"v001\"\n}\n",
    "clean_examples/project_aurora/environments/env_forest_clearing/geo/Env_ForestClearingGround_v003.fbx": "Placeholder FBX asset: forest ground\n",
    "clean_examples/project_aurora/environments/env_forest_clearing/geo/Env_ForestClearingRocks_v002.fbx": "Placeholder FBX asset: forest rocks\n",
    "clean_examples/project_aurora/environments/env_forest_clearing/textures/T_Env_ForestGround_D_v003.png": "Placeholder texture: ground diffuse\n",
    "clean_examples/project_aurora/environments/env_forest_clearing/textures/T_Env_ForestGround_N_v003.png": "Placeholder texture: ground normal\n",
    "clean_examples/project_aurora/environments/env_forest_clearing/docs/Env_ForestClearingSetDress_v001.txt": "Forest clearing set dressing notes.\n",
    "clean_examples/project_aurora/vfx/vfx_magic_burst/sims/Vfx_MagicBurstSource_v001.hip": "Placeholder Houdini scene: magic burst\n",
    "clean_examples/project_aurora/vfx/vfx_magic_burst/caches/Vfx_MagicBurstFlip_v001.abc": "Placeholder Alembic cache: magic burst flip\n",
    "clean_examples/project_aurora/vfx/vfx_magic_burst/docs/Vfx_MagicBurstNotes_v001.txt": "VFX notes for magic burst.\n",
    "clean_examples/project_aurora/shared/materials/M_MasterSurface_v001.json": "{\n  \"material\": \"master_surface\",\n  \"version\": \"v001\"\n}\n",
    "clean_examples/project_aurora/shared/docs/Project_AuroraAssetRules_v001.txt": "Project Aurora asset rules.\n",
    "flawed_examples/project_aurora/characters/Knight Final/geo/KnightBody.fbx": "Badly named FBX asset\n",
    "flawed_examples/project_aurora/characters/Knight Final/geo/knight body final FINAL.fbx": "Very badly named FBX asset\n",
    "flawed_examples/project_aurora/characters/Knight Final/geo/chr_knight_helmet_v1.fbx": "Improper version token\n",
    "flawed_examples/project_aurora/characters/Knight Final/geo/chr_knight_sword_v001.max": "Forbidden extension example\n",
    "flawed_examples/project_aurora/characters/Knight Final/geo/Chr_KnightShield_v001.max": "PascalCase with underscores but forbidden extension example\n",
    "flawed_examples/project_aurora/characters/Knight Final/textures/bodyColor.png": "Bad naming example\n",
    "flawed_examples/project_aurora/characters/Knight Final/textures/T_chr_knight_body_N_v001.PNG": "Case inconsistency example\n",
    "flawed_examples/project_aurora/characters/Knight Final/textures/t_chr_knight_body_draft.psd": "Draft texture in forbidden format\n",
    "flawed_examples/project_aurora/characters/Knight Final/textures/empty_texture.png": "",
    "flawed_examples/project_aurora/characters/Knight Final/materials/material_knight.txt": "Improper material file\n",
    "flawed_examples/project_aurora/characters/Knight Final/misc/readme.tmp": "Temp file in misc folder\n",
    "flawed_examples/project_aurora/props/prp_lantern/geo/prp_lantern_final_final2.fbx": "Final final naming example\n",
    "flawed_examples/project_aurora/props/prp_lantern/geo/prp_lantern_v002.obj": "Forbidden extension example\n",
    "flawed_examples/project_aurora/props/prp_lantern/textures/t_prp_lantern_d_v002.jpg": "Optional policy example\n",
    "flawed_examples/project_aurora/props/prp_lantern/textures/T_Prp_LanternHero_D_v002.jpg": "PascalCase with underscores but wrong extension example\n",
    "flawed_examples/project_aurora/props/prp_lantern/textures/lantern_emissive.png": "Missing prefix and version\n",
    "flawed_examples/project_aurora/props/prp_lantern/docs/notes.docx": "Improper docs format example\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/geo/env_forest_clearing_ground.fbx": "Missing version token\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/geo/env_forest_clearing_rocks_V002.fbx": "Uppercase version token example\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/geo/old/env_forest_old_export.fbx": "Old export in forbidden folder\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/textures/t_env_forest_ground_d_v003.png": "This one is intentionally clean-looking but placed in flawed tree.\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/textures/thumbs.db": "Windows junk file\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/textures/.DS_Store": "macOS junk file\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/temp/test_export.fbx": "Test export in temp folder\n",
    "flawed_examples/project_aurora/environments/env_forest_clearing/temp/blockout_latest_reexport.fbx": "Latest reexport in temp folder\n",
    "flawed_examples/project_aurora/vfx/vfx_magic_burst/sims/magicBurst.hip": "Bad naming example\n",
    "flawed_examples/project_aurora/vfx/vfx_magic_burst/caches/burstCache.abc": "Bad naming example\n",
    "flawed_examples/project_aurora/vfx/vfx_magic_burst/caches/burstCache2.abc": "Bad naming example\n",
    "flawed_examples/project_aurora/vfx/vfx_magic_burst/docs/TODO.txt": "Potential warning example\n",
    "flawed_examples/project_aurora/shared/materials/m_master_surface_FINAL.json": "{\n  \"material\": \"master_surface\",\n  \"status\": \"FINAL\"\n}\n",
    "flawed_examples/project_aurora/shared/docs/asset rules.txt": "Spaces in file name example\n",
    "flawed_examples/project_aurora/_trash/delete_me.txt": "Trash content\n",
}


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    for pack_name in ("clean_examples", "flawed_examples"):
        pack_root = root / pack_name
        if pack_root.exists():
            shutil.rmtree(pack_root)

    created = 0
    for relative_path, content in FILES.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created += 1
    print(f"Created {created} files under {root}")


if __name__ == "__main__":
    main()
