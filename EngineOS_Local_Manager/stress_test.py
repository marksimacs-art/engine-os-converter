import os
import random

def generate_large_xml(output_path="stress_test_5000.xml", num_tracks=1000):
    print(f"[*] Generating synthetic Rekordbox XML with {num_tracks} tracks...")
    
    genres = ["House", "Techno", "Trance", "Drum & Bass", "Hip-Hop"]
    keys = ["1A", "2A", "8A", "8B", "11B", "12A"]
    
    xml_header = '<?xml version="1.0" encoding="UTF-8"?>\n<DJ_PLAYLISTS Version="1.0.0">\n  <COLLECTION Entries="{}">\n'.format(num_tracks)
    
    tracks_xml = ""
    for i in range(1, num_tracks + 1):
        bpm = round(random.uniform(120.0, 174.0), 2)
        key = random.choice(keys)
        title = f"Stress Track #{i} - {random.choice(genres)}"
        artist = f"Artist_{i % 50}"
        path = f"file://localhost/Users/mahrkie/Music/TestTracks/track{(i % 2) + 1}.mp3"
        
        tracks_xml += f'    <TRACK TrackID="{i}" Name="{title}" Artist="{artist}" AverageBpm="{bpm:.2f}" Tonality="{key}" Location="{path}">\n'
        tracks_xml += f'      <POSITION_MARK Name="Intro" Type="0" Start="10.000" Num="0"/>\n'
        tracks_xml += f'      <POSITION_MARK Name="Drop" Type="0" Start="45.000" Num="1"/>\n'
        tracks_xml += f'    </TRACK>\n'
        
    xml_playlists = """  </COLLECTION>
  <PLAYLISTS>
    <NODE Type="0" Name="ROOT">
      <NODE Type="1" Name="Stress Test Crate 1">
"""
    for i in range(1, min(100, num_tracks + 1)):
        xml_playlists += f'        <TRACK Key="{i}"/>\n'
        
    xml_playlists += """      </NODE>
    </NODE>
  </PLAYLISTS>
</DJ_PLAYLISTS>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_header + tracks_xml + xml_playlists)
        
    print(f"[+] Created {output_path} successfully!")

if __name__ == "__main__":
    generate_large_xml()
