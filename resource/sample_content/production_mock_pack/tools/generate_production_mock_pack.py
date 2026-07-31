from __future__ import annotations

import shutil
from collections import Counter
from pathlib import Path


PACK_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_ROOT = PACK_ROOT / "project_nebula"


def touch(relative_path: str) -> None:
    path = OUTPUT_ROOT / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def version(number: int) -> str:
    return f"v{number:03d}"


def add_character_assets(counts: Counter[str]) -> None:
    characters = [
        "chr_ranger",
        "chr_engineer",
        "chr_pilot",
        "chr_medic",
        "chr_scout",
        "chr_heavy",
        "chr_smuggler",
        "chr_android",
        "chr_captain",
        "chr_technician",
    ]
    for index, asset in enumerate(characters, start=1):
        root = f"characters/{asset}"
        files = [
            f"{root}/geo/{asset}_body_{version(1)}.fbx",
            f"{root}/geo/{asset}_head_{version(1)}.fbx",
            f"{root}/geo/{asset}_lod1_{version(1)}.fbx",
            f"{root}/source/{asset}_body_{version(1)}.ma",
            f"{root}/textures/t_{asset}_body_d_{version(1)}.png",
            f"{root}/textures/t_{asset}_body_n_{version(1)}.png",
            f"{root}/textures/t_{asset}_body_r_{version(1)}.png",
            f"{root}/textures/t_{asset}_head_d_{version(1)}.png",
            f"{root}/textures/t_{asset}_head_n_{version(1)}.png",
            f"{root}/materials/m_{asset}_body_{version(1)}.json",
            f"{root}/materials/m_{asset}_head_{version(1)}.json",
            f"{root}/rig/{asset}_skeleton_{version(1)}.fbx",
            f"{root}/anim/{asset}_idle_{version(1)}.fbx",
            f"{root}/docs/{asset}_notes_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["character"] += 1


def add_prop_assets(counts: Counter[str]) -> None:
    props = [
        "prp_crate",
        "prp_barrel",
        "prp_console",
        "prp_generator",
        "prp_terminal",
        "prp_container",
        "prp_forklift",
        "prp_drone_pad",
        "prp_streetlight",
        "prp_bench",
        "prp_locker",
        "prp_holo_table",
        "prp_cable_reel",
        "prp_security_gate",
        "prp_pipe_bundle",
        "prp_roof_fan",
        "prp_med_station",
        "prp_canister",
        "prp_cargo_pallet",
        "prp_tool_cart",
        "prp_monitor_wall",
        "prp_server_rack",
        "prp_generator_small",
        "prp_panel_array",
        "prp_repair_bot",
        "prp_scaffold",
        "prp_door_frame",
        "prp_bridge_support",
        "prp_radio_tower",
        "prp_nav_beacon",
    ]
    for index, asset in enumerate(props, start=1):
        root = f"props/{asset}"
        files = [
            f"{root}/geo/{asset}_{version(1)}.fbx",
            f"{root}/geo/{asset}_lod1_{version(1)}.fbx",
            f"{root}/source/{asset}_{version(1)}.ma",
            f"{root}/textures/t_{asset}_d_{version(1)}.png",
            f"{root}/textures/t_{asset}_n_{version(1)}.png",
            f"{root}/textures/t_{asset}_m_{version(1)}.png",
            f"{root}/materials/m_{asset}_{version(1)}.json",
            f"{root}/docs/{asset}_usage_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["prop"] += 1


def add_environment_assets(counts: Counter[str]) -> None:
    environments = [
        "env_hangar_a",
        "env_hangar_b",
        "env_market_street",
        "env_cargo_bay",
        "env_reactor_core",
        "env_rooftop_garden",
        "env_service_tunnel",
        "env_research_lab",
        "env_command_bridge",
        "env_landing_pad",
        "env_residential_block",
        "env_waste_processing",
    ]
    for index, asset in enumerate(environments, start=1):
        root = f"environments/{asset}"
        files = [
            f"{root}/geo/{asset}_shell_{version(2)}.fbx",
            f"{root}/geo/{asset}_setdress_{version(2)}.fbx",
            f"{root}/geo/{asset}_collision_{version(1)}.fbx",
            f"{root}/source/{asset}_blockout_{version(3)}.ma",
            f"{root}/textures/t_{asset}_trim_d_{version(2)}.png",
            f"{root}/textures/t_{asset}_trim_n_{version(2)}.png",
            f"{root}/textures/t_{asset}_decal_m_{version(1)}.png",
            f"{root}/materials/m_{asset}_master_{version(1)}.json",
            f"{root}/lighting/{asset}_lookdev_{version(1)}.json",
            f"{root}/docs/{asset}_setdress_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["environment"] += 1


def add_weapon_assets(counts: Counter[str]) -> None:
    weapons = [
        "wpn_rifle",
        "wpn_pistol",
        "wpn_shotgun",
        "wpn_sniper",
        "wpn_smg",
        "wpn_energy_blade",
        "wpn_plasma_launcher",
        "wpn_stun_baton",
        "wpn_repair_tool",
        "wpn_signal_flare",
        "wpn_emp_device",
        "wpn_grenade_launcher",
    ]
    for index, asset in enumerate(weapons, start=1):
        root = f"weapons/{asset}"
        files = [
            f"{root}/geo/{asset}_{version(1)}.fbx",
            f"{root}/geo/{asset}_lod1_{version(1)}.fbx",
            f"{root}/source/{asset}_{version(1)}.ma",
            f"{root}/textures/t_{asset}_d_{version(1)}.png",
            f"{root}/textures/t_{asset}_n_{version(1)}.png",
            f"{root}/textures/t_{asset}_m_{version(1)}.png",
            f"{root}/materials/m_{asset}_{version(1)}.json",
            f"{root}/anim/{asset}_reload_{version(1)}.fbx",
            f"{root}/docs/{asset}_spec_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["weapon"] += 1


def add_vehicle_assets(counts: Counter[str]) -> None:
    vehicles = [
        "veh_cargo_truck",
        "veh_hover_bike",
        "veh_dropship",
        "veh_service_cart",
        "veh_patrol_car",
        "veh_loader_mech",
        "veh_mining_rig",
        "veh_escape_pod",
    ]
    for index, asset in enumerate(vehicles, start=1):
        root = f"vehicles/{asset}"
        files = [
            f"{root}/geo/{asset}_body_{version(1)}.fbx",
            f"{root}/geo/{asset}_interior_{version(1)}.fbx",
            f"{root}/geo/{asset}_lod1_{version(1)}.fbx",
            f"{root}/source/{asset}_{version(2)}.ma",
            f"{root}/textures/t_{asset}_body_d_{version(1)}.png",
            f"{root}/textures/t_{asset}_body_n_{version(1)}.png",
            f"{root}/textures/t_{asset}_glass_m_{version(1)}.png",
            f"{root}/materials/m_{asset}_body_{version(1)}.json",
            f"{root}/materials/m_{asset}_glass_{version(1)}.json",
            f"{root}/docs/{asset}_maintenance_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["vehicle"] += 1


def add_vfx_assets(counts: Counter[str]) -> None:
    effects = [
        "vfx_thruster_trail",
        "vfx_sparks_welder",
        "vfx_smoke_vent",
        "vfx_energy_shield",
        "vfx_alarm_flash",
        "vfx_reactor_leak",
        "vfx_hologram_boot",
        "vfx_dust_falloff",
        "vfx_landing_pad_steam",
        "vfx_emp_burst",
    ]
    for index, asset in enumerate(effects, start=1):
        root = f"vfx/{asset}"
        files = [
            f"{root}/sims/{asset}_source_{version(1)}.hip",
            f"{root}/caches/{asset}_flip_{version(1)}.abc",
            f"{root}/textures/t_{asset}_flip_d_{version(1)}.png",
            f"{root}/textures/t_{asset}_mask_{version(1)}.png",
            f"{root}/materials/m_{asset}_{version(1)}.json",
            f"{root}/niagara/ns_{asset}_{version(1)}.uasset",
            f"{root}/docs/{asset}_notes_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["vfx"] += 1


def add_ui_assets(counts: Counter[str]) -> None:
    widgets = [
        "hud_health_bar",
        "hud_shield_meter",
        "hud_objective_banner",
        "hud_weapon_swap",
        "menu_pause",
        "menu_inventory",
        "menu_loadout",
        "menu_map",
        "menu_crafting",
        "menu_settings",
        "ui_prompt_interact",
        "ui_prompt_hack",
        "ui_prompt_pickup",
        "ui_prompt_repair",
        "ui_reticle_precision",
        "ui_reticle_heavy",
        "ui_notification_loot",
        "ui_notification_alarm",
        "ui_terminal_boot",
        "ui_terminal_error",
    ]
    for index, asset in enumerate(widgets, start=1):
        root = f"ui/{asset}"
        files = [
            f"{root}/textures/t_{asset}_d_{version(1)}.png",
            f"{root}/source/{asset}_{version(1)}.psd",
            f"{root}/widgets/wbp_{asset}_{version(1)}.uasset",
            f"{root}/docs/{asset}_layout_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["ui"] += 1


def add_audio_assets(counts: Counter[str]) -> None:
    events = [
        "amb_hangar_loop",
        "amb_market_crowd",
        "amb_reactor_hum",
        "amb_rooftop_wind",
        "sfx_door_slide",
        "sfx_console_boot",
        "sfx_alarm_short",
        "sfx_alarm_long",
        "sfx_weapon_rifle_fire",
        "sfx_weapon_shotgun_fire",
        "sfx_weapon_reload",
        "sfx_emp_burst",
        "sfx_hover_bike_pass",
        "sfx_dropship_land",
        "sfx_ui_click",
        "sfx_ui_confirm",
        "sfx_ui_error",
        "vox_control_room_callout",
        "vox_pilot_warning",
        "vox_engineer_status",
        "mus_menu_theme",
        "mus_combat_loop",
        "mus_escape_stinger",
        "mus_victory_tag",
    ]
    for index, asset in enumerate(events, start=1):
        root = f"audio/{asset}"
        files = [
            f"{root}/wav/{asset}_{version(1)}.wav",
            f"{root}/metadata/{asset}_{version(1)}.json",
            f"{root}/banks/{asset}_{version(1)}.uasset",
            f"{root}/docs/{asset}_notes_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["audio"] += 1


def add_cinematics(counts: Counter[str]) -> None:
    sequences = [
        "seq_intro_arrival",
        "seq_bridge_alarm",
        "seq_hangar_escape",
        "seq_market_meet",
        "seq_reactor_shutdown",
        "seq_final_departure",
    ]
    for index, asset in enumerate(sequences, start=1):
        root = f"cinematics/{asset}"
        files = [
            f"{root}/shots/{asset}_layout_{version(1)}.ma",
            f"{root}/cameras/{asset}_cam_{version(1)}.fbx",
            f"{root}/audio/{asset}_scratch_{version(1)}.wav",
            f"{root}/sequences/ls_{asset}_{version(1)}.uasset",
            f"{root}/renders/{asset}_preview_{version(1)}.mov",
            f"{root}/docs/{asset}_beat_sheet_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["cinematic"] += 1


def add_system_assets(counts: Counter[str]) -> None:
    systems = [
        "bp_interaction_terminal",
        "bp_security_door",
        "bp_lift_platform",
        "bp_loot_container",
        "bp_alarm_beacon",
        "bp_mission_tracker",
        "bp_objective_marker",
        "bp_damage_volume",
        "bp_checkpoint_trigger",
        "bp_inventory_station",
        "bp_repair_station",
        "bp_data_pad",
        "bp_patrol_path",
        "bp_camera_rig",
        "bp_turret_defense",
        "bp_vendor_kiosk",
    ]
    for index, asset in enumerate(systems, start=1):
        root = f"systems/{asset}"
        files = [
            f"{root}/blueprints/{asset}_{version(1)}.uasset",
            f"{root}/data/{asset}_{version(1)}.json",
            f"{root}/docs/{asset}_setup_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["system"] += 1


def add_shared_assets(counts: Counter[str]) -> None:
    for index in range(1, 19):
        files = [
            f"shared/materials/m_master_surface_{version(index)}.json",
            f"shared/shaders/sh_surface_layer_{version(index)}.usf",
            f"shared/docs/pipeline_rule_set_{version(index)}.txt",
        ]
        for file_path in files:
            touch(file_path)
            counts["shared"] += 1

    for index in range(1, 13):
        files = [
            f"shared/config/render_profile_{version(index)}.ini",
            f"shared/config/validation_profile_{version(index)}.json",
        ]
        for file_path in files:
            touch(file_path)
            counts["shared"] += 1


def add_intentional_failures(counts: Counter[str]) -> None:
    invalid_files = [
        "_trash/delete_me.txt",
        "_trash/old/final_list.xlsx",
        "characters/Character Final/geo/KnightBody.fbx",
        "characters/Character Final/geo/chr_knight_body_final_FINAL.fbx",
        "characters/Character Final/textures/T_chr_knight_body_D_v001.PNG",
        "characters/Character Final/textures/chr_knight_diffuse latest.png",
        "characters/Character Final/textures/t_chr_knight_body_draft.psd",
        "characters/Character Final/misc/readme.tmp",
        "characters/chr_ranger/temp/chr_ranger_body_reexport_latest.fbx",
        "characters/chr_engineer/backup/chr_engineer_body_v001_copy.fbx",
        "characters/chr_pilot/geo/chr_pilot_head_v1.fbx",
        "characters/chr_android/textures/thumbs.db",
        "characters/chr_captain/textures/.DS_Store",
        "props/prp_console/geo/prp_console_final_final2.obj",
        "props/prp_bench/textures/prp_bench_color.jpg",
        "props/prp_barrel/docs/notes.docx",
        "props/prp_tool_cart/temp/test_export.fbx",
        "props/prp_nav_beacon/old/prp_nav_beacon_blockout.fbx",
        "props/prp_server_rack/misc/keep_me.blend",
        "environments/env_market_street/temp/blockout_latest_reexport.fbx",
        "environments/env_market_street/textures/thumbs.db",
        "environments/env_reactor_core/textures/T_env_reactor_core_trim_D_v001.PNG",
        "environments/env_service_tunnel/geo/env_service_tunnel_shell_V002.fbx",
        "environments/env_service_tunnel/geo/old/env_service_tunnel_archive.fbx",
        "environments/env_landing_pad/docs/asset rules.txt",
        "vehicles/veh_dropship/geo/veh_dropship FINAL.fbx",
        "vehicles/veh_loader_mech/textures/veh_loader_mech_body_diffuse.png",
        "vehicles/veh_escape_pod/temp/veh_escape_pod_latest.fbx",
        "weapons/wpn_rifle/geo/wpn_rifle_high.max",
        "weapons/wpn_plasma_launcher/textures/t_wpn_plasma_launcher_d_v001.jpg",
        "weapons/wpn_emp_device/misc/wpn_emp_device_notes.tmp",
        "weapons/wpn_signal_flare/geo/wpn signal flare v001.fbx",
        "vfx/vfx_thruster_trail/caches/burstCache.abc",
        "vfx/vfx_alarm_flash/docs/TODO.txt",
        "vfx/vfx_emp_burst/temp/vfx_emp_burst_latest.hip",
        "vfx/vfx_smoke_vent/textures/t_vfx_smoke_vent_draft.psd",
        "ui/menu_pause/source/Menu Pause Final.psd",
        "ui/ui_notification_alarm/textures/ui_notification_alarm_final.png",
        "ui/ui_terminal_error/widgets/WBP_ui_terminal_error.uasset",
        "audio/sfx_alarm_long/wav/sfx_alarm_long_FINAL.wav",
        "audio/mus_menu_theme/wav/mus menu theme v001.wav",
        "audio/vox_pilot_warning/metadata/vox_pilot_warning_v1.json",
        "audio/amb_market_crowd/backup/amb_market_crowd_notes.txt",
        "cinematics/seq_intro_arrival/renders/seq_intro_arrival_preview_latest.mov",
        "cinematics/seq_market_meet/shots/old/seq_market_meet_layout.fbx",
        "cinematics/seq_final_departure/docs/final beats.txt",
        "systems/bp_alarm_beacon/data/bp_alarm_beacon_FINAL.json",
        "systems/bp_vendor_kiosk/misc/readme.tmp",
        "systems/bp_camera_rig/blueprints/BP_Camera_Rig_v001.uasset",
        "reviews/may_review_drop/character final.fbx",
        "reviews/may_review_drop/heroMesh_latest.fbx",
        "reviews/may_review_drop/weapon_draft.fbx",
        "reviews/may_review_drop/thumbs.db",
        "vendor_delivery/external_vendor/drop_01/fx_test.blend",
        "vendor_delivery/external_vendor/drop_01/read me.txt",
        "vendor_delivery/external_vendor/drop_01/final/fx_cache_latest.abc",
    ]
    for file_path in invalid_files:
        touch(file_path)
        counts["invalid"] += 1

    invalid_batches = [
        ("incoming/unsorted_drop", "asset", "fbx", 16),
        ("incoming/unsorted_drop", "latest_export", "fbx", 12),
        ("incoming/unsorted_drop", "texture_draft", "png", 12),
        ("incoming/client_notes", "review_notes", "docx", 10),
        ("migration/old_assets", "archive_mesh", "obj", 12),
        ("migration/old_assets", "archive_texture", "jpg", 12),
        ("sandbox/temp_exports", "playblast", "mov", 8),
        ("sandbox/temp_exports", "blockout", "fbx", 8),
    ]
    for folder, stem, extension, count in invalid_batches:
        for index in range(1, count + 1):
            touch(f"{folder}/{stem}_{index:02d}.{extension}")
            counts["invalid"] += 1


def build_pack() -> Counter[str]:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)

    counts: Counter[str] = Counter()
    add_character_assets(counts)
    add_prop_assets(counts)
    add_environment_assets(counts)
    add_weapon_assets(counts)
    add_vehicle_assets(counts)
    add_vfx_assets(counts)
    add_ui_assets(counts)
    add_audio_assets(counts)
    add_cinematics(counts)
    add_system_assets(counts)
    add_shared_assets(counts)
    add_intentional_failures(counts)
    return counts


def main() -> None:
    counts = build_pack()
    total = sum(counts.values())
    print(f"Created {total} files under {OUTPUT_ROOT}")
    for name in sorted(counts):
        print(f"{name}: {counts[name]}")


if __name__ == "__main__":
    main()
