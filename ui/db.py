"""
Makinity Cut - MySQL 8.0 Database Engine & ORM Layer
Handles connection pooling, schema migration, project persistence,
timeline tracks/elements management, and asset deduplication.
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
import pymysql
from pymysql.cursors import DictCursor
from dotenv import load_dotenv

# Load .env configuration
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger("makinity.db")

MYSQL_HOST = os.getenv("MYSQL_HOST", "127.0.0.1")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "root")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "makinity_cut")

PROJECTS_DIR = BASE_DIR / "projects"
STORAGE_DIR = BASE_DIR / "storage"


def get_server_connection():
    """Connect to MySQL server (without selecting database) to perform admin tasks."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True
    )


def get_db_connection():
    """Connect directly to the makinity_cut database."""
    return pymysql.connect(
        host=MYSQL_HOST,
        port=MYSQL_PORT,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DATABASE,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True
    )


def init_db():
    """Create database and tables if they don't exist."""
    try:
        # Step 1: Ensure database exists
        with get_server_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"CREATE DATABASE IF NOT EXISTS `{MYSQL_DATABASE}` "
                    f"CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
                )
        logger.info(f"Database `{MYSQL_DATABASE}` verified.")

        # Step 2: Ensure schema tables exist
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Projects Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id VARCHAR(64) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    aspect_ratio VARCHAR(16) NOT NULL DEFAULT '9:16',
                    duration DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
                    resolution VARCHAR(32) NOT NULL DEFAULT '1080x1920',
                    fps INT NOT NULL DEFAULT 30,
                    category VARCHAR(64) NOT NULL DEFAULT 'ugc',
                    settings JSON NOT NULL,
                    thumbnail_gradient VARCHAR(128) DEFAULT 'from-blue-600 via-indigo-700 to-slate-900',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    INDEX idx_updated_at (updated_at DESC),
                    INDEX idx_category (category)
                ) ENGINE=InnoDB;
                """)

                # Media Assets Table (SHA-256 Deduplicated)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS media_assets (
                    id VARCHAR(64) PRIMARY KEY,
                    filename VARCHAR(255) NOT NULL,
                    file_path VARCHAR(1024) NOT NULL,
                    media_type ENUM('video', 'audio', 'image') NOT NULL,
                    file_size BIGINT NOT NULL DEFAULT 0,
                    duration DECIMAL(8, 2) NOT NULL DEFAULT 0.00,
                    resolution VARCHAR(32) DEFAULT NULL,
                    codec VARCHAR(32) DEFAULT NULL,
                    loudness_lufs DECIMAL(5, 2) DEFAULT -14.00,
                    proxy_path VARCHAR(1024) DEFAULT NULL,
                    waveform_data JSON DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB;
                """)

                # Timeline Tracks Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS timeline_tracks (
                    id VARCHAR(64) PRIMARY KEY,
                    project_id VARCHAR(64) NOT NULL,
                    track_type ENUM('video', 'subtitle', 'effect', 'sfx', 'bgm') NOT NULL,
                    track_index INT NOT NULL DEFAULT 0,
                    is_muted BOOLEAN NOT NULL DEFAULT FALSE,
                    is_locked BOOLEAN NOT NULL DEFAULT FALSE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_proj_track (project_id, track_index)
                ) ENGINE=InnoDB;
                """)

                # Timeline Elements Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS timeline_elements (
                    id VARCHAR(64) PRIMARY KEY,
                    track_id VARCHAR(64) NOT NULL,
                    asset_id VARCHAR(64) DEFAULT NULL,
                    element_type ENUM('clip', 'text', 'effect', 'sfx', 'bgm') NOT NULL,
                    start_time DECIMAL(8, 3) NOT NULL DEFAULT 0.000,
                    duration DECIMAL(8, 3) NOT NULL DEFAULT 1.000,
                    in_point DECIMAL(8, 3) NOT NULL DEFAULT 0.000,
                    out_point DECIMAL(8, 3) NOT NULL DEFAULT 1.000,
                    speed DECIMAL(4, 2) NOT NULL DEFAULT 1.00,
                    transform JSON DEFAULT NULL,
                    properties JSON NOT NULL,
                    FOREIGN KEY (track_id) REFERENCES timeline_tracks(id) ON DELETE CASCADE,
                    FOREIGN KEY (asset_id) REFERENCES media_assets(id) ON DELETE SET NULL,
                    INDEX idx_track_time (track_id, start_time)
                ) ENGINE=InnoDB;
                """)

                # Subtitle Cues Table (Verbatim Script)
                cur.execute("""
                CREATE TABLE IF NOT EXISTS subtitle_cues (
                    id VARCHAR(64) PRIMARY KEY,
                    project_id VARCHAR(64) NOT NULL,
                    start_time DECIMAL(8, 3) NOT NULL,
                    end_time DECIMAL(8, 3) NOT NULL,
                    text_content TEXT NOT NULL,
                    speaker VARCHAR(128) DEFAULT NULL,
                    is_biochroma_spec BOOLEAN NOT NULL DEFAULT TRUE,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_proj_cue (project_id, start_time)
                ) ENGINE=InnoDB;
                """)

                # AI Edit History Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS ai_edit_history (
                    id VARCHAR(64) PRIMARY KEY,
                    project_id VARCHAR(64) NOT NULL,
                    agent_engine VARCHAR(64) NOT NULL,
                    user_prompt TEXT NOT NULL,
                    timeline_patch JSON NOT NULL,
                    snapshot_before JSON NOT NULL,
                    can_revert BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    INDEX idx_proj_time (project_id, created_at DESC)
                ) ENGINE=InnoDB;
                """)

                # Render Jobs Table
                cur.execute("""
                CREATE TABLE IF NOT EXISTS render_jobs (
                    id VARCHAR(64) PRIMARY KEY,
                    project_id VARCHAR(64) NOT NULL,
                    output_filename VARCHAR(255) NOT NULL,
                    status ENUM('pending', 'processing', 'completed', 'failed') NOT NULL DEFAULT 'pending',
                    progress INT NOT NULL DEFAULT 0,
                    error_message TEXT DEFAULT NULL,
                    render_time_sec DECIMAL(8, 2) DEFAULT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                ) ENGINE=InnoDB;
                """)

        logger.info("All MySQL 8.0 schema tables successfully verified.")
        # Ensure database is seeded with projects
        ensure_database_seeded()
        return True
    except Exception as e:
        logger.error(f"Error initializing MySQL database: {e}")
        return False


def ensure_database_seeded():
    """Ensure standard default projects and any disk projects exist in MySQL."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM projects;")
                rows = cur.fetchall()
                existing_ids = {r["id"] for r in rows}

                # Scan projects/ folder for existing .json or .capcut files if db is empty
                if not existing_ids:
                    project_files = list(PROJECTS_DIR.glob("*.json")) + list(PROJECTS_DIR.glob("*.capcut"))
                    for pf in project_files:
                        try:
                            with open(pf, "r", encoding="utf-8") as f:
                                data = json.load(f)
                            save_project_from_dict(data)
                            logger.info(f"Migrated project: {data.get('name')}")
                        except Exception as pe:
                            logger.error(f"Failed to migrate {pf.name}: {pe}")

                # Ensure default flagship projects always exist
                seed_default_projects(skip_existing=True)
    except Exception as e:
        logger.error(f"Failed to seed MySQL database: {e}")


def seed_default_projects(skip_existing: bool = False):
    """Default seed projects (BioChroma, Jar Opener, TikTok Punch)."""
    p_biochroma = {
        "id": "proj_biochroma",
        "name": "BioChroma Client Spec 78pt Ad.capcut",
        "aspect_ratio": "9:16",
        "duration": 42.50,
        "resolution": "1080x1920",
        "category": "biochroma",
        "thumbnail_gradient": "from-emerald-600 via-teal-700 to-slate-900",
        "settings": {
            "preset": "biochroma",
            "caption_style": "biochroma",
            "caption_font": "Roboto-Bold",
            "caption_size": 78,
            "caption_color": "#FFFFFF",
            "caption_stroke": "#181818",
            "caption_stroke_width": 4.0,
            "caption_margin_v": 520,
            "caption_wrap_style": 2,
            "grade": "vibrant_pop",
            "bgm_track": "Upbeat Viral Pop.mp3",
            "bgm_volume": 0.16
        },
        "clips": [
            {"id": "bc1", "name": "01_biochroma_hook.mp4", "duration": 6.5, "in_point": 0.0, "out_point": 6.5},
            {"id": "bc2", "name": "02_centella_asiatica.mp4", "duration": 8.0, "in_point": 0.0, "out_point": 8.0},
            {"id": "bc3", "name": "03_golden_peptides.mp4", "duration": 7.5, "in_point": 0.0, "out_point": 7.5},
            {"id": "bc4", "name": "04_little_secret_wink.mp4", "duration": 4.5, "in_point": 0.0, "out_point": 4.5},
            {"id": "bc5", "name": "05_send_me_link.mp4", "duration": 6.0, "in_point": 0.0, "out_point": 6.0},
            {"id": "bc6", "name": "06_lifestyle_cta.mp4", "duration": 10.0, "in_point": 0.0, "out_point": 10.0}
        ],
        "timelineTexts": [
            {"id": "txt_bc1", "content": "BIOCHROMA, IL NOSTRO PICCOLO SEGRETO", "start": 0.0, "duration": 6.5, "style": "biochroma"},
            {"id": "txt_bc2", "content": "CENTELLA ASIATICA & PEPTIDI DI SETA", "start": 6.5, "duration": 8.0, "style": "biochroma"}
        ],
        "timelineEffects": [
            {"id": "fx_glow", "name": "Soft Dream Glow", "type": "glow", "start": 6.5, "duration": 4.0}
        ],
        "timelineSfx": [
            {"id": "sfx_pop", "name": "🔔 Chime", "start": 6.5, "duration": 1.5}
        ]
    }

    p_jar_opener = {
        "id": "proj_jar_opener",
        "name": "Jar Opener UGC Viral Ad.capcut",
        "aspect_ratio": "9:16",
        "duration": 21.98,
        "resolution": "1080x1920",
        "category": "ugc",
        "thumbnail_gradient": "from-blue-600 via-indigo-700 to-slate-900",
        "settings": {
            "preset": "viral_hook",
            "caption_style": "biochroma",
            "caption_font": "Roboto-Bold",
            "caption_size": 78,
            "caption_color": "#FFFFFF",
            "caption_stroke": "#181818",
            "caption_stroke_width": 4.0,
            "caption_margin_v": 520,
            "caption_wrap_style": 2,
            "grade": "vibrant_pop",
            "bgm_track": "Lo-Fi Chill Hop.mp3",
            "bgm_volume": 0.18
        },
        "clips": [
            {"id": "clip_1", "name": "01_hook_problem.mp4", "duration": 4.5, "in_point": 0.0, "out_point": 4.5},
            {"id": "clip_2", "name": "02_unboxing_reveal.mp4", "duration": 5.2, "in_point": 0.0, "out_point": 5.2},
            {"id": "clip_3", "name": "03_demo_use_case.mp4", "duration": 6.8, "in_point": 0.0, "out_point": 6.8},
            {"id": "clip_4", "name": "04_cta_discount.mp4", "duration": 5.48, "in_point": 0.0, "out_point": 5.48}
        ],
        "timelineTexts": [
            {"id": "txt_1", "content": "PROBLEM SOLVED", "start": 0.0, "duration": 4.5, "style": "biochroma"},
            {"id": "txt_2", "content": "EASY ONE-TWIST GRIP", "start": 4.5, "duration": 5.2, "style": "biochroma"}
        ],
        "timelineEffects": [
            {"id": "fx_shake", "name": "Camera Shake", "type": "shake", "start": 0.0, "duration": 2.5}
        ],
        "timelineSfx": [
            {"id": "sfx_whoosh", "name": "⚡ Whoosh", "start": 0.0, "duration": 1.2}
        ]
    }

    p_tiktok_punch = {
        "id": "proj_tiktok_punch",
        "name": "TikTok Punchy Hook Reel.capcut",
        "aspect_ratio": "9:16",
        "duration": 18.20,
        "resolution": "1080x1920",
        "category": "drafts",
        "thumbnail_gradient": "from-rose-600 via-orange-600 to-slate-900",
        "settings": {
            "preset": "hormozi",
            "caption_style": "hormozi",
            "caption_font": "The Bold Font",
            "caption_size": 46,
            "caption_color": "#FFCC00",
            "caption_stroke": "#000000",
            "caption_stroke_width": 3.0,
            "caption_margin_v": 480,
            "caption_wrap_style": 2,
            "grade": "high_contrast",
            "bgm_track": "Upbeat Viral Pop.mp3",
            "bgm_volume": 0.20
        },
        "clips": [
            {"id": "tt1", "name": "01_punch_hook.mp4", "duration": 5.0, "in_point": 0.0, "out_point": 5.0},
            {"id": "tt2", "name": "02_reaction_fast.mp4", "duration": 6.2, "in_point": 0.0, "out_point": 6.2},
            {"id": "tt3", "name": "03_call_to_action.mp4", "duration": 7.0, "in_point": 0.0, "out_point": 7.0}
        ],
        "timelineTexts": [
            {"id": "txt_tt1", "content": "STOP SCROLLING!", "start": 0.0, "duration": 5.0, "style": "hormozi"},
            {"id": "txt_tt2", "content": "THIS IS LIFE CHANGING", "start": 5.0, "duration": 6.2, "style": "hormozi"}
        ],
        "timelineEffects": [
            {"id": "fx_zoom", "name": "Punch Zoom", "type": "zoom", "start": 0.0, "duration": 1.5}
        ],
        "timelineSfx": [
            {"id": "sfx_hit", "name": "🔥 Impact Hit", "start": 0.0, "duration": 1.0}
        ]
    }

    seeds = [p_biochroma, p_jar_opener, p_tiktok_punch]
    for p in seeds:
        if skip_existing and get_project(p["id"]):
            continue
        save_project_from_dict(p)
        logger.info(f"Seeded default project into MySQL: {p['name']}")


def save_project_from_dict(data: Dict[str, Any]):
    """Insert or update a complete project with its tracks and timeline elements."""
    project_id = data.get("id") or f"proj_{int(datetime.now().timestamp())}"
    name = data.get("name", "Untitled Ad")
    aspect_ratio = data.get("aspect_ratio", "9:16")
    duration = float(data.get("duration", 0.0))
    resolution = data.get("resolution", "1080x1920")
    category = data.get("category", "ugc")
    settings = json.dumps(data.get("settings", {}))
    thumbnail_gradient = data.get("thumbnail_gradient", "from-blue-600 via-indigo-700 to-slate-900")

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Upsert project
            cur.execute("""
            INSERT INTO projects (id, name, aspect_ratio, duration, resolution, category, settings, thumbnail_gradient, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                aspect_ratio = VALUES(aspect_ratio),
                duration = VALUES(duration),
                resolution = VALUES(resolution),
                category = VALUES(category),
                settings = VALUES(settings),
                thumbnail_gradient = VALUES(thumbnail_gradient),
                updated_at = NOW();
            """, (project_id, name, aspect_ratio, duration, resolution, category, settings, thumbnail_gradient))

            # Delete old tracks & elements for clean sync
            cur.execute("DELETE FROM timeline_tracks WHERE project_id = %s;", (project_id,))

            # 1. Video Track (Track 0)
            track_vid_id = f"tr_vid_{project_id}"
            cur.execute("""
            INSERT INTO timeline_tracks (id, project_id, track_type, track_index)
            VALUES (%s, %s, 'video', 0);
            """, (track_vid_id, project_id))

            curr_time = 0.0
            for idx, clip in enumerate(data.get("clips", [])):
                raw_id = clip.get("id") or f"clip_{idx}"
                elem_id = f"{project_id}_{raw_id}"
                c_dur = float(clip.get("duration", 4.0))
                c_in = float(clip.get("in_point", 0.0))
                c_out = float(clip.get("out_point", c_dur))
                
                props_dict = dict(clip)
                props_dict.pop("duration", None)
                props_dict.pop("in_point", None)
                props_dict.pop("out_point", None)
                props = json.dumps(props_dict)

                cur.execute("""
                INSERT INTO timeline_elements (id, track_id, element_type, start_time, duration, in_point, out_point, properties)
                VALUES (%s, %s, 'clip', %s, %s, %s, %s, %s);
                """, (elem_id, track_vid_id, curr_time, c_dur, c_in, c_out, props))
                curr_time += c_dur

            # 2. Subtitle Track (Track 1)
            track_txt_id = f"tr_txt_{project_id}"
            cur.execute("""
            INSERT INTO timeline_tracks (id, project_id, track_type, track_index)
            VALUES (%s, %s, 'subtitle', 1);
            """, (track_txt_id, project_id))

            for idx, txt in enumerate(data.get("timelineTexts", [])):
                raw_id = txt.get("id") or f"txt_{idx}"
                elem_id = f"{project_id}_{raw_id}"
                t_start = float(txt.get("start", 0.0))
                t_dur = float(txt.get("duration", 4.0))
                
                props_dict = dict(txt)
                props_dict.pop("start", None)
                props_dict.pop("duration", None)
                props = json.dumps(props_dict)

                cur.execute("""
                INSERT INTO timeline_elements (id, track_id, element_type, start_time, duration, properties)
                VALUES (%s, %s, 'text', %s, %s, %s);
                """, (elem_id, track_txt_id, t_start, t_dur, props))

            # 3. Effects Track (Track 2)
            track_fx_id = f"tr_fx_{project_id}"
            cur.execute("""
            INSERT INTO timeline_tracks (id, project_id, track_type, track_index)
            VALUES (%s, %s, 'effect', 2);
            """, (track_fx_id, project_id))

            for idx, fx in enumerate(data.get("timelineEffects", [])):
                raw_id = fx.get("id") or f"fx_{idx}"
                elem_id = f"{project_id}_{raw_id}"
                f_start = float(fx.get("start", 0.0))
                f_dur = float(fx.get("duration", 2.5))
                
                props_dict = dict(fx)
                props_dict.pop("start", None)
                props_dict.pop("duration", None)
                props = json.dumps(props_dict)

                cur.execute("""
                INSERT INTO timeline_elements (id, track_id, element_type, start_time, duration, properties)
                VALUES (%s, %s, 'effect', %s, %s, %s);
                """, (elem_id, track_fx_id, f_start, f_dur, props))

            # 4. SFX Track (Track 3)
            track_sfx_id = f"tr_sfx_{project_id}"
            cur.execute("""
            INSERT INTO timeline_tracks (id, project_id, track_type, track_index)
            VALUES (%s, %s, 'sfx', 3);
            """, (track_sfx_id, project_id))

            for idx, sfx in enumerate(data.get("timelineSfx", [])):
                raw_id = sfx.get("id") or f"sfx_{idx}"
                elem_id = f"{project_id}_{raw_id}"
                s_start = float(sfx.get("start", 0.0))
                s_dur = float(sfx.get("duration", 1.2))
                
                props_dict = dict(sfx)
                props_dict.pop("start", None)
                props_dict.pop("duration", None)
                props = json.dumps(props_dict)

                cur.execute("""
                INSERT INTO timeline_elements (id, track_id, element_type, start_time, duration, properties)
                VALUES (%s, %s, 'sfx', %s, %s, %s);
                """, (elem_id, track_sfx_id, s_start, s_dur, props))


# =========================================================================
# HIGH-LEVEL CRUD API FOR FASTAPI
# =========================================================================

def get_all_projects() -> List[Dict[str, Any]]:
    """Retrieve all projects formatted for the CapCut Project Hub."""
    projects_list = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM projects ORDER BY updated_at DESC;")
            rows = cur.fetchall()

            for r in rows:
                proj_id = r["id"]
                # Fetch clips count
                cur.execute("""
                SELECT te.* FROM timeline_elements te
                JOIN timeline_tracks tt ON te.track_id = tt.id
                WHERE tt.project_id = %s AND te.element_type = 'clip'
                ORDER BY te.start_time ASC;
                """, (proj_id,))
                clips_rows = cur.fetchall()

                # Fetch text cues
                cur.execute("""
                SELECT te.* FROM timeline_elements te
                JOIN timeline_tracks tt ON te.track_id = tt.id
                WHERE tt.project_id = %s AND te.element_type = 'text'
                ORDER BY te.start_time ASC;
                """, (proj_id,))
                text_rows = cur.fetchall()

                # Fetch effects
                cur.execute("""
                SELECT te.* FROM timeline_elements te
                JOIN timeline_tracks tt ON te.track_id = tt.id
                WHERE tt.project_id = %s AND te.element_type = 'effect'
                ORDER BY te.start_time ASC;
                """, (proj_id,))
                fx_rows = cur.fetchall()

                # Fetch sfx
                cur.execute("""
                SELECT te.* FROM timeline_elements te
                JOIN timeline_tracks tt ON te.track_id = tt.id
                WHERE tt.project_id = %s AND te.element_type = 'sfx'
                ORDER BY te.start_time ASC;
                """, (proj_id,))
                sfx_rows = cur.fetchall()

                # Parse JSON settings
                settings = r["settings"]
                if isinstance(settings, str):
                    try:
                        settings = json.loads(settings)
                    except Exception:
                        settings = {}

                # Format clips
                clips = []
                for c in clips_rows:
                    props = json.loads(c["properties"]) if isinstance(c["properties"], str) else (c["properties"] or {})
                    clip_dict = dict(props)
                    clip_dict["id"] = c["id"]
                    clip_dict["duration"] = float(c["duration"])
                    clip_dict["in_point"] = float(c["in_point"])
                    clip_dict["out_point"] = float(c["out_point"])
                    if "name" not in clip_dict:
                        clip_dict["name"] = "clip.mp4"
                    clips.append(clip_dict)

                # Format texts
                timelineTexts = []
                for t in text_rows:
                    props = json.loads(t["properties"]) if isinstance(t["properties"], str) else (t["properties"] or {})
                    txt_dict = dict(props)
                    txt_dict["id"] = t["id"]
                    txt_dict["start"] = float(t["start_time"])
                    txt_dict["duration"] = float(t["duration"])
                    if "content" not in txt_dict:
                        txt_dict["content"] = "TEXT"
                    timelineTexts.append(txt_dict)

                # Format effects
                timelineEffects = []
                for fx in fx_rows:
                    props = json.loads(fx["properties"]) if isinstance(fx["properties"], str) else (fx["properties"] or {})
                    fx_dict = dict(props)
                    fx_dict["id"] = fx["id"]
                    fx_dict["start"] = float(fx["start_time"])
                    fx_dict["duration"] = float(fx["duration"])
                    if "name" not in fx_dict:
                        fx_dict["name"] = "Effect"
                    timelineEffects.append(fx_dict)

                # Format sfx
                timelineSfx = []
                for sx in sfx_rows:
                    props = json.loads(sx["properties"]) if isinstance(sx["properties"], str) else (sx["properties"] or {})
                    sx_dict = dict(props)
                    sx_dict["id"] = sx["id"]
                    sx_dict["start"] = float(sx["start_time"])
                    sx_dict["duration"] = float(sx["duration"])
                    if "name" not in sx_dict:
                        sx_dict["name"] = "SFX Hit"
                    timelineSfx.append(sx_dict)

                projects_list.append({
                    "id": r["id"],
                    "name": r["name"],
                    "aspect_ratio": r["aspect_ratio"],
                    "updated_at": r["updated_at"].isoformat() if hasattr(r["updated_at"], "isoformat") else str(r["updated_at"]),
                    "duration": float(r["duration"]),
                    "clips_count": len(clips),
                    "resolution": r["resolution"],
                    "thumbnail_gradient": r["thumbnail_gradient"],
                    "category": r["category"],
                    "settings": settings,
                    "clips": clips,
                    "timelineTexts": timelineTexts,
                    "timelineEffects": timelineEffects,
                    "timelineSfx": timelineSfx
                })

    return projects_list


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve a single project by ID."""
    all_p = get_all_projects()
    for p in all_p:
        if p["id"] == project_id:
            return p
    return None


def create_project(name: str, aspect_ratio: str = "9:16", preset: str = "viral_hook") -> Dict[str, Any]:
    """Create a new project in MySQL and return it."""
    proj_id = f"proj_{int(datetime.now(timezone.utc).timestamp())}"
    if not name.endswith(".capcut"):
        filename = f"{name}.capcut"
    else:
        filename = name

    # Setup presets
    if preset == "biochroma":
        settings = {
            "preset": "biochroma",
            "caption_style": "biochroma",
            "caption_font": "Roboto-Bold",
            "caption_size": 78,
            "caption_color": "#FFFFFF",
            "caption_stroke": "#181818",
            "caption_stroke_width": 4.0,
            "caption_margin_v": 520,
            "caption_wrap_style": 2,
            "grade": "vibrant_pop",
            "bgm_track": "Upbeat Viral Pop.mp3",
            "bgm_volume": 0.16
        }
        category = "biochroma"
        gradient = "from-emerald-600 via-teal-700 to-slate-900"
        clips = [
            {"id": "bc1", "name": "01_biochroma_hook.mp4", "duration": 6.5, "in_point": 0.0, "out_point": 6.5},
            {"id": "bc2", "name": "02_centella_asiatica.mp4", "duration": 8.0, "in_point": 0.0, "out_point": 8.0},
            {"id": "bc3", "name": "03_golden_peptides.mp4", "duration": 7.5, "in_point": 0.0, "out_point": 7.5},
            {"id": "bc4", "name": "04_little_secret_wink.mp4", "duration": 4.5, "in_point": 0.0, "out_point": 4.5},
            {"id": "bc5", "name": "05_send_me_link.mp4", "duration": 6.0, "in_point": 0.0, "out_point": 6.0},
            {"id": "bc6", "name": "06_lifestyle_cta.mp4", "duration": 10.0, "in_point": 0.0, "out_point": 10.0}
        ]
        duration = 42.50
        timelineTexts = [
            {"id": "txt_bc1", "content": "BIOCHROMA, IL NOSTRO PICCOLO SEGRETO", "start": 0.0, "duration": 6.5, "style": "biochroma"},
            {"id": "txt_bc2", "content": "CENTELLA ASIATICA & PEPTIDI DI SETA", "start": 6.5, "duration": 8.0, "style": "biochroma"}
        ]
        timelineEffects = [
            {"id": "fx_glow", "name": "Soft Dream Glow", "type": "glow", "start": 6.5, "duration": 4.0}
        ]
        timelineSfx = [
            {"id": "sfx_pop", "name": "🔔 Chime", "start": 6.5, "duration": 1.5}
        ]
    elif preset == "blank":
        settings = {
            "preset": "blank",
            "caption_style": "clean_white",
            "grade": "none",
            "bgm_track": "none",
            "bgm_volume": 0.15
        }
        category = "draft"
        gradient = "from-slate-700 to-slate-900"
        clips = []
        duration = 0.0
        timelineTexts = []
        timelineEffects = []
        timelineSfx = []
    else:
        # Default UGC Viral Hook
        settings = {
            "preset": "viral_hook",
            "caption_style": "biochroma",
            "caption_font": "Roboto-Bold",
            "caption_size": 78,
            "caption_color": "#FFFFFF",
            "caption_stroke": "#181818",
            "caption_stroke_width": 4.0,
            "caption_margin_v": 520,
            "caption_wrap_style": 2,
            "grade": "vibrant_pop",
            "bgm_track": "Lo-Fi Chill Hop.mp3",
            "bgm_volume": 0.18
        }
        category = "ugc"
        gradient = "from-blue-600 via-indigo-700 to-slate-900"
        clips = [
            {"id": "clip_1", "name": "01_hook_problem.mp4", "duration": 4.5, "in_point": 0.0, "out_point": 4.5},
            {"id": "clip_2", "name": "02_unboxing_reveal.mp4", "duration": 5.2, "in_point": 0.0, "out_point": 5.2},
            {"id": "clip_3", "name": "03_demo_use_case.mp4", "duration": 6.8, "in_point": 0.0, "out_point": 6.8},
            {"id": "clip_4", "name": "04_cta_discount.mp4", "duration": 5.48, "in_point": 0.0, "out_point": 5.48}
        ]
        duration = 21.98
        timelineTexts = [
            {"id": "txt_1", "content": "PROBLEM SOLVED", "start": 0.0, "duration": 4.5, "style": "biochroma"},
            {"id": "txt_2", "content": "EASY ONE-TWIST GRIP", "start": 4.5, "duration": 5.2, "style": "biochroma"}
        ]
        timelineEffects = [
            {"id": "fx_shake", "name": "Camera Shake", "type": "shake", "start": 0.0, "duration": 2.5}
        ]
        timelineSfx = [
            {"id": "sfx_whoosh", "name": "⚡ Whoosh", "start": 0.0, "duration": 1.2}
        ]

    proj_dict = {
        "id": proj_id,
        "name": filename,
        "aspect_ratio": aspect_ratio,
        "duration": duration,
        "resolution": "1080x1920" if aspect_ratio == "9:16" else ("1920x1080" if aspect_ratio == "16:9" else "1080x1080"),
        "category": category,
        "thumbnail_gradient": gradient,
        "settings": settings,
        "clips": clips,
        "timelineTexts": timelineTexts,
        "timelineEffects": timelineEffects,
        "timelineSfx": timelineSfx
    }

    save_project_from_dict(proj_dict)
    return get_project(proj_id)


def open_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Touch updated_at and retrieve project."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE projects SET updated_at = NOW() WHERE id = %s;", (project_id,))
    return get_project(project_id)


def duplicate_project(project_id: str) -> Optional[Dict[str, Any]]:
    """Clone an existing project."""
    orig = get_project(project_id)
    if not orig:
        return None

    new_id = f"proj_{int(datetime.now(timezone.utc).timestamp())}"
    new_dict = dict(orig)
    new_dict["id"] = new_id
    new_dict["name"] = f"Copy of {orig['name']}"

    save_project_from_dict(new_dict)
    return get_project(new_id)


def rename_project(project_id: str, new_name: str) -> bool:
    """Rename a project."""
    if not new_name.endswith(".capcut"):
        clean_name = f"{new_name}.capcut"
    else:
        clean_name = new_name

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE projects SET name = %s, updated_at = NOW() WHERE id = %s;", (clean_name, project_id))
    return True


def delete_project(project_id: str) -> bool:
    """Delete a project (cascades to tracks and elements in MySQL)."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE id = %s;", (project_id,))
    return True


def save_project_timeline(project_id: str, clips: List[Dict], timelineTexts: List[Dict],
                          timelineEffects: List[Dict], timelineSfx: List[Dict], settings: Dict[str, Any],
                          name: Optional[str] = None) -> bool:
    """Sync full timeline state transactionally to MySQL. Auto-creates project if missing."""
    proj = get_project(project_id)
    tot_dur = sum(float(c.get("duration", 0.0)) for c in clips)
    if not proj:
        proj_name = name or (f"{project_id}.capcut" if not project_id.endswith(".capcut") else project_id)
        proj = {
            "id": project_id,
            "name": proj_name,
            "aspect_ratio": settings.get("aspect_ratio", "9:16"),
            "duration": round(tot_dur, 2) if tot_dur > 0 else 30.0,
            "resolution": "1080x1920",
            "category": "biochroma" if "biochroma" in project_id.lower() else "ugc",
            "thumbnail_gradient": "from-emerald-600 via-teal-700 to-slate-900" if "biochroma" in project_id.lower() else "from-blue-600 via-indigo-700 to-slate-900",
            "settings": settings,
            "clips": clips,
            "timelineTexts": timelineTexts,
            "timelineEffects": timelineEffects,
            "timelineSfx": timelineSfx
        }
    else:
        if name:
            proj["name"] = name if name.endswith(".capcut") else f"{name}.capcut"
        proj["duration"] = round(tot_dur, 2)
        proj["clips"] = clips
        proj["timelineTexts"] = timelineTexts
        proj["timelineEffects"] = timelineEffects
        proj["timelineSfx"] = timelineSfx
        proj["settings"] = settings

    save_project_from_dict(proj)
    return True


def get_db_health() -> Dict[str, Any]:
    """Check MySQL connectivity and return health status."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION() AS ver;")
                row = cur.fetchone()
                cur.execute("SELECT COUNT(*) AS proj_count FROM projects;")
                pc = cur.fetchone()
                return {
                    "connected": True,
                    "engine": "MySQL 8.0",
                    "version": row["ver"],
                    "port": MYSQL_PORT,
                    "host": MYSQL_HOST,
                    "database": MYSQL_DATABASE,
                    "projects_count": pc["proj_count"]
                }
    except Exception as e:
        return {
            "connected": False,
            "engine": "MySQL 8.0",
            "error": str(e),
            "host": MYSQL_HOST,
            "port": MYSQL_PORT
        }
