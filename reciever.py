import socket
import struct
import pandas as pd
import shutil
from pathlib import Path
import os
import glob
import json
from track_ids import TRACKS
# Setup where the packets are received from
UDP_IP = "127.0.0.1"
UDP_PORT = 20777
HEADER_SIZE = 29

# Init socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

with open("./ready/ready.txt", "w") as file:
    file.write("Receiver is Ready")

print(f"Listening for sockets on {UDP_IP}:{UDP_PORT}")

track_map_data = {"corners": []}

current_data = {}
telemetry_rows = []
last_lap = 1

best_lap_dir = 'best_lap/'
last_lap_dir = 'last_lap/'

current_uid = None


os.makedirs(best_lap_dir, exist_ok=True)
os.makedirs(last_lap_dir, exist_ok=True)
os.makedirs("lap_data/", exist_ok=True)

def move_best(name): 
    best_dir = Path('./best_lap')
    track_dir = Path(f'./track_laps/{name}')
    best_file = list(best_dir.glob("*.csv"))

    if best_file:
        shutil.move(best_file[0], track_dir)
    else:
        print("Failed to move file")

while True:
    best_lap_files = glob.glob(os.path.join(best_lap_dir, '*'))
    best_lap_file = best_lap_files[0] if best_lap_files else None

    last_lap_files = glob.glob(os.path.join(last_lap_dir, '*'))
    last_lap_file = last_lap_files[0] if last_lap_files else None

    data, addr = sock.recvfrom(2048)

    # CRITICAL: Ensure [0] is present here
    packet_id = struct.unpack('<B', data[6:7])[0]
    player_index = struct.unpack('<B', data[27:28])[0]

    # Car Telemetry Packet
    if packet_id == 6:
        CAR_TELEMETRY_SIZE = 60
        player_offset = HEADER_SIZE + (player_index * CAR_TELEMETRY_SIZE)
        
        # CRITICAL: Ensure [0] is present here
        current_data['speed'] = struct.unpack('<H', data[player_offset:player_offset+2])[0]
        current_data['throttle'] = struct.unpack('<f', data[player_offset+2:player_offset+6])[0]
        current_data['brake'] = struct.unpack('<f', data[player_offset+10:player_offset+14])[0]

        telemetry_rows.append(current_data.copy())

    # Lap Data Packet
    elif packet_id == 2:
        LAP_DATA_SIZE = 57
        player_offset = HEADER_SIZE + (player_index * LAP_DATA_SIZE)

        # CRITICAL: Ensure [0] is present here
        current_data['lap'] = struct.unpack('<B', data[player_offset+33:player_offset+34])[0]
        current_data['lap_time'] = struct.unpack('<I', data[player_offset+4:player_offset+8])[0] / 1000
        current_data['distance'] = struct.unpack('<f', data[player_offset+20:player_offset+24])[0]

        next_corner = "Unknown/Main Straight" 
        for corner in track_map_data['corners']:
            if corner['apex'] > current_data['distance']:
                next_corner = corner['name']
                break

        current_data['next_corner'] = next_corner
        telemetry_rows.append(current_data.copy())

        # Lap Change Triggered
        if current_data['lap'] != last_lap:
            print(f"Lap changed from {last_lap} to {current_data['lap']}. Processing telemetry...")
            
            df = pd.DataFrame(telemetry_rows)
            
            if not df.empty and 'lap' in df.columns:
                target_lap = current_data['lap'] - 1
                df = df[df['lap'] == target_lap]
                
                if "lap_time" in df.columns:
                    df["lap_time"] = pd.to_numeric(df["lap_time"], errors="coerce")
                    df = df[df["lap_time"] > 0].reset_index(drop=True)
                
                if "distance" in df.columns:
                    df = df[df["distance"].diff().fillna(0) >= 0]
                
                if 'speed' in df.columns and not df.empty:
                    csv_filename = f'lap_{target_lap}_data.csv'
                    
                    if not os.listdir(best_lap_dir):
                        df.to_csv(os.path.join(best_lap_dir, csv_filename), index=False)
                        print(f"Initial bench lap saved: {csv_filename}")
                    else:
                        best_df = pd.read_csv(best_lap_file)
                        if best_df.iloc[-1]['lap_time'] > df.iloc[-1]['lap_time']:
                            if best_lap_file and os.path.exists(best_lap_file):
                                shutil.move(best_lap_file, "lap_data/")
                            df.to_csv(os.path.join(best_lap_dir, csv_filename), index=False)
                            print(f"New personal best! Saved: {csv_filename}")
                        else:
                            if last_lap_file and os.path.exists(last_lap_file):
                                os.remove(last_lap_file)
                            df.to_csv(os.path.join(last_lap_dir, csv_filename), index=False)
                            print(f"Lap completed. Saved to last_lap: {csv_filename}")
                else:
                    print("Telemetry dataframe was empty after filtering out lap rows.")
            else:
                print("No data rows found matching the recorded laps.")
            
            telemetry_rows = []
            last_lap = current_data['lap']
            
    elif packet_id == 1:
        # CRITICAL: Ensure [0] is present here
        current_data['track_id'] = struct.unpack('<b', data[HEADER_SIZE+7:HEADER_SIZE+8])[0]
        track_path = os.path.join("tracks", TRACKS[current_data['track_id']]['file'])
    
        track_dir = f'./track_laps/{TRACKS[current_data['track_id']]['name']}'
        if not (os.path.isdir(track_dir)):
            os.mkdir(track_dir)

        try:
            with open(track_path) as file:
                track_map_data = json.load(file)
        except FileNotFoundError:
            print(f'{track_path} was not found')

        session_uid = struct.unpack_from('<Q', data, 7)[0]
        current_track = TRACKS[current_data['track_id']]['name']

        if current_uid == None:
            current_uid = session_uid
        elif current_uid != session_uid:
            print("NEW SESSION")
            move_best(current_track)
            current_uid = session_uid
            

