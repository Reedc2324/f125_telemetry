import socket
import struct
import pandas as pd
import shutil
import os
import glob
import json

# Setup where the packets are recieved from
UDP_IP = "127.0.0.1"
UDP_PORT = 20777

# Sizes of packets
HEADER_SIZE = 29

# Init socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"Listening for sockets on {UDP_IP}:{UDP_PORT}")

current_data = {}
telemetry_rows = []

last_lap = 1

best_lap_dir = 'best_lap/'

best_lap_file = None



while True:
    if not os.listdir(best_lap_dir):
        best_lap_file = None
    else:
        best_lap_file = glob.glob(f'{best_lap_dir}*')[0]

    data, addr = sock.recvfrom(2048)

    packet_id = struct.unpack('<B', data[6:7])[0]
    player_index = struct.unpack('<B', data[27:28])[0]

        

    

    # Car Telemetry Packet
    if packet_id == 6:
        CAR_TELEMETRY_SIZE = 60
        player_offset = HEADER_SIZE + (player_index * CAR_TELEMETRY_SIZE)
        
        current_data['speed'] = struct.unpack('<H', data[player_offset:player_offset+2])[0]
        current_data['throttle'] = struct.unpack('<f', data[player_offset+2:player_offset+6])[0]
        current_data['brake'] = struct.unpack('<f', data[player_offset+10:player_offset+14])[0]

        telemetry_rows.append(current_data.copy())

    # Lap Data Packet
    elif packet_id == 2:
        LAP_DATA_SIZE = 57
        player_offset = HEADER_SIZE + (player_index * LAP_DATA_SIZE)

        current_data['lap'] = struct.unpack('<B', data[player_offset+33:player_offset+34])[0]
        current_data['lap_time'] = struct.unpack('<I', data[player_offset+4:player_offset+8])[0] / 1000
        current_data['distance'] = struct.unpack('<f', data[player_offset+20:player_offset+24])[0]

        with open('tracks/austria.json') as file:
                data = json.load(file)

                for corner in data['corners']:
                    if corner['apex'] > current_data['distance']:
                        next_corner = corner['name']
                        break

        current_data['next_corner'] = next_corner

        telemetry_rows.append(current_data.copy())

        if current_data['lap'] != last_lap:
            df = pd.DataFrame(telemetry_rows)
            df = df[df['lap'] == current_data['lap']-1]
            df["lap_time"] = pd.to_numeric(df["lap_time"], errors="coerce")
            df = df[df["lap_time"] > 0].reset_index(drop=True)
            df = df[df["distance"].diff().fillna(0) >= 0]
            
            

            # Check if the last completed lap was real
            if 'speed' in df:
                # If there is no bench lap set make the next completed lap the bench
                if not os.listdir(best_lap_dir):
                    df.to_csv(f'{best_lap_dir}/lap_{current_data['lap'] - 1}_data')
                    telemetry_rows = []
                else:
                    best_df = pd.read_csv(best_lap_file)
                    # See if the new lap is faster than the bench lap
                    if best_df.iloc[-1]['lap_time'] > df.iloc[-1]['lap_time']:
                        shutil.move(best_lap_file, "lap_data/")
                        df.to_csv(f'{best_lap_dir}/lap_{current_data['lap'] - 1}_data')
                        telemetry_rows = []
                    else:
                        df.to_csv(f'lap_data/lap_{current_data['lap'] - 1}_data')
                    
                    
        
        last_lap = current_data['lap']
    elif packet_id == 1:
        current_data['track_id'] = struct.unpack('<b', data[HEADER_SIZE+24:HEADER_SIZE+25])[0]
        print(current_data['track_id'])
        
        


    