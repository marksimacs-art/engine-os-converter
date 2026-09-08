import os
import sys
import sqlite3
import shutil
import uuid
import argparse
import logging
import urllib.parse
import xml.etree.ElementTree as ET

logging.basicConfig(
    filename="conversion_report.log",
    filemode="w",
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

KEY_MAP = {
    "1A": "1A", "1B": "1B", "2A": "2A", "2B": "2B", "3A": "3A", "3B": "3B",
    "4A": "4A", "4B": "4B", "5A": "5A", "5B": "5B", "6A": "6A", "6B": "6B",
    "7A": "7A", "7B": "7B", "8A": "8A", "8B": "8B", "9A": "9A", "9B": "9B",
    "10A": "10A", "10B": "10B", "11A": "11A", "11B": "11B", "12A": "12A", "12B": "12B",
    "Abm": "1A", "B": "1B", "Ebm": "2A", "F#": "2B", "Bbm": "3A", "Db": "3B",
    "Fm": "4A", "Ab": "4B", "Cm": "5A", "Eb": "5B", "Gm": "6A", "Bb": "6B",
    "Dm": "7A", "F": "7B", "Am": "8A", "C": "8B", "Em": "9A", "G": "9B",
    "Bm": "10A", "D": "10B", "F#m": "11A", "A": "11B", "C#m": "12A", "E": "12B"
}

class EngineOSMasterPipeline:
    def __init__(self, drive_root_path: str):
        self.drive_root = os.path.abspath(drive_root_path)
        self.db_dir = os.path.join(self.drive_root, "Engine Library", "Database2")
        self.music_dir = os.path.join(self.drive_root, "Music")
        self.m_db_path = os.path.join(self.db_dir, "m.db")
        self.p_db_path = os.path.join(self.db_dir, "p.db")
        
        self.m_conn = None
        self.p_conn = None

    def initialize_drive_environment(self):
        """Creates Engine OS directory trees and enforces WAL journal mode."""
        os.makedirs(self.db_dir, exist_ok=True)
        os.makedirs(self.music_dir, exist_ok=True)

        self.m_conn = sqlite3.connect(self.m_db_path, timeout=10.0)
        self.p_conn = sqlite3.connect(self.p_db_path, timeout=10.0)

        self.m_conn.execute("PRAGMA journal_mode=WAL;")
        self.p_conn.execute("PRAGMA journal_mode=WAL;")

        self.m_conn.execute("""
            CREATE TABLE IF NOT EXISTS Track (
                id INTEGER PRIMARY KEY, path TEXT UNIQUE, title TEXT, artist TEXT, 
                bpm INTEGER, key TEXT, isAnalyzed INTEGER, 
                originDatabaseUuid TEXT, originId INTEGER, dateAdded TEXT
            );
        """)
        self.m_conn.execute("""
            CREATE TABLE IF NOT EXISTS Playlist (
                id INTEGER PRIMARY KEY, title TEXT UNIQUE, parentId INTEGER DEFAULT 0
            );
        """)
        self.m_conn.execute("""
            CREATE TABLE IF NOT EXISTS PlaylistTrack (
                id INTEGER PRIMARY KEY, playlistId INTEGER, trackId INTEGER, listOrder INTEGER
            );
        """)
        self.p_conn.execute("""
            CREATE TABLE IF NOT EXISTS PerformanceData (
                id INTEGER PRIMARY KEY, trackId INTEGER, type INTEGER, 
                indexNumber INTEGER, position INTEGER, endPosition INTEGER, label TEXT
            );
        """)
        self.m_conn.commit()
        self.p_conn.commit()
        print(f"[+] Engine OS Environment Initialized at: {self.drive_root}")

    def normalize_key(self, raw_key: str) -> str:
        if not raw_key:
            return "8A"
        return KEY_MAP.get(raw_key.strip(), raw_key.strip())

    def import_rekordbox_xml(self, xml_path: str):
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"XML file not found: {xml_path}")

        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        db_uuid = str(uuid.uuid4())
        m_cursor = self.m_conn.cursor()
        p_cursor = self.p_conn.cursor()

        track_id_map = {}
        copied_files = 0
        missing_files = 0

        for track in root.findall(".//COLLECTION/TRACK"):
            rk_id = track.get("TrackID")
            title = track.get("Name", "Unknown Title")
            artist = track.get("Artist", "Unknown Artist")
            bpm = float(track.get("AverageBpm", 120.0))
            raw_key = track.get("Tonality", "")
            normalized_key = self.normalize_key(raw_key)
            
            raw_location = track.get("Location", "")
            clean_uri = urllib.parse.unquote(raw_location)
            src_file_path = clean_uri.replace("file://localhost", "")

            dest_relative_path = f"Music/{os.path.basename(src_file_path)}"
            dest_full_path = os.path.join(self.drive_root, dest_relative_path)

            if os.path.exists(src_file_path):
                try:
                    shutil.copy2(src_file_path, dest_full_path)
                    copied_files += 1
                except Exception as e:
                    logging.warning(f"Could not copy {src_file_path}: {e}")

            m_cursor.execute("""
                INSERT OR IGNORE INTO Track (path, title, artist, bpm, key, isAnalyzed, originDatabaseUuid, originId, dateAdded)
                VALUES (?, ?, ?, ?, ?, 1, ?, ?, datetime('now'));
            """, (dest_relative_path, title, artist, int(bpm * 100), normalized_key, db_uuid, rk_id))
            
            m_cursor.execute("SELECT id FROM Track WHERE path = ?;", (dest_relative_path,))
            row = m_cursor.fetchone()
            engine_track_id = row[0] if row else m_cursor.lastrowid
            track_id_map[rk_id] = engine_track_id

            for position in track.findall("POSITION_MARK"):
                cue_type = int(position.get("Type", "0"))
                cue_num = int(position.get("Num", 0))
                start_sec = float(position.get("Start", 0.0))
                end_sec = float(position.get("End", 0.0)) if position.get("End") else 0.0
                label = position.get("Name", f"Cue {cue_num + 1}")

                p_cursor.execute("""
                    INSERT INTO PerformanceData (trackId, type, indexNumber, position, endPosition, label)
                    VALUES (?, ?, ?, ?, ?, ?);
                """, (engine_track_id, cue_type, cue_num, int(start_sec * 1000), int(end_sec * 1000), label))

        def parse_node(node_elem, parent_db_id=0):
            node_type = node_elem.get("Type")
            node_name = node_elem.get("Name", "Untitled")

            if node_type == "0" and node_name != "ROOT":
                m_cursor.execute("INSERT OR IGNORE INTO Playlist (title, parentId) VALUES (?, ?);", (node_name, parent_db_id))
                m_cursor.execute("SELECT id FROM Playlist WHERE title = ?;", (node_name,))
                current_id = m_cursor.fetchone()[0]
                for child in node_elem:
                    if child.tag == "NODE":
                        parse_node(child, current_id)
            elif node_type == "1":
                m_cursor.execute("INSERT OR IGNORE INTO Playlist (title, parentId) VALUES (?, ?);", (node_name, parent_db_id))
                m_cursor.execute("SELECT id FROM Playlist WHERE title = ?;", (node_name,))
                playlist_id = m_cursor.fetchone()[0]

                for order, track_node in enumerate(node_elem.findall("TRACK")):
                    rk_track_id = track_node.get("Key")
                    if rk_track_id in track_id_map:
                        engine_track_id = track_id_map[rk_track_id]
                        m_cursor.execute("""
                            INSERT INTO PlaylistTrack (playlistId, trackId, listOrder)
                            VALUES (?, ?, ?);
                        """, (playlist_id, engine_track_id, order))
            else:
                for child in node_elem:
                    if child.tag == "NODE":
                        parse_node(child, parent_db_id)

        root_playlists = root.find(".//PLAYLISTS")
        if root_playlists is not None:
            parse_node(root_playlists)

        self.m_conn.commit()
        self.p_conn.commit()

    def close(self):
        if self.m_conn:
            self.m_conn.commit()
            self.m_conn.close()
        if self.p_conn:
            self.p_conn.commit()
            self.p_conn.close()

def detect_usb_drives():
    volumes = "/Volumes"
    if not os.path.exists(volumes):
        return []
    
    ignore_names = {"macintosh hd", "docker", "recovery", "com.apple"}
    drives = []
    
    for entry in os.listdir(volumes):
        full_path = os.path.join(volumes, entry)
        if os.path.isdir(full_path) and not entry.startswith("."):
            if any(ignored in entry.lower() for ignored in ignore_names):
                continue
            drives.append(full_path)
                
    return drives
