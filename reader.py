import pandas as pd
import glob
import json
from pathlib import Path
import os
import time
from track_ids import TRACKS

best_lap = glob.glob('best_lap/*')[0]


def best_lap_brake_dist():
    df = pd.read_csv(best_lap)
    non_zero_rows = df[df['brake'] != 0]
    first_brake = non_zero_rows.groupby('next_corner', as_index=False).first().sort_values(by='distance')
    braked_corners = set(first_brake["next_corner"])
    with open('tracks/austria.json') as file:
        data = json.load(file)
        for corner in data['corners']:
            if corner['name'] not in braked_corners:
                print(f'{corner['name']} taken flat out')
            else:
                brake = first_brake[first_brake["next_corner"] == corner["name"]].iloc[0]
                braking_distance = corner['apex'] - brake['distance']
                print(
                    f"You braked {braking_distance:.1f}m "
                    f"before the apex of {corner['name']}"
                )
            print()

def lap_brake_dist(lap_num):
    df = pd.read_csv(f"lap_data/lap_{lap_num}_data")
    non_zero_rows = df[df['brake'] != 0]
    first_brake = non_zero_rows.groupby('next_corner', as_index=False).first().sort_values(by='distance')
    braked_corners = set(first_brake["next_corner"])
    with open('tracks/austria.json') as file:
        data = json.load(file)
        for corner in data['corners']:
            if corner['name'] not in braked_corners:
                print(f'{corner['name']} taken flat out')
            else:
                brake = first_brake[first_brake["next_corner"] == corner["name"]].iloc[0]
                braking_distance = corner['apex'] - brake['distance']
                print(
                    f"You braked {braking_distance:.1f}m "
                    f"before the apex of {corner['name']}"
                )
            print()

def main():
    lap_choice = input("What lap data would you like to see? (type best to see your fastest lap)").strip()

    file_path = Path(f'lap_data/lap_{lap_choice}_data')

    if lap_choice == "best":
        best_lap_brake_dist()
    elif file_path.is_file():
        lap_brake_dist(lap_choice)
    else:
        print("Please Select a valid lap!")
        time.sleep(3)
        os.system('cls' if os.name == 'nt' else 'clear')
        main()
    

if __name__ == "__main__":
    os.system('cls' if os.name == 'nt' else 'clear')
    main()