import tkinter as tk
from tkinter import ttk
import pandas as pd
import glob
import os
import subprocess
from pathlib import Path
import sys
import threading
import psutil

class F1LapTelemetryDashboard:
    def __init__(self, root):
        self.root = root
        self.root.title("F1 Performance Telemetry Analyzer")
        self.root.geometry("600x480")
        self.root.configure(bg="#121214")
        
        # Target paths pointing directly to your recorder folders
        self.best_lap_dir = 'best_lap/'
        self.last_lap_dir = 'last_lap/'
        
        # Track the last seen file modification timestamps to prevent duplicate reading
        self.last_seen_best_time = 0.0
        self.last_seen_recent_time = 0.0
        
        # UI Styling Definitions
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TLabel", background="#121214", foreground="#a0a0a5", font=("Arial", 11))
        style.configure("Header.TLabel", font=("Arial", 12, "bold"), foreground="#ffea00")
        style.configure("MetricName.TLabel", font=("Arial", 10, "bold"), foreground="#e1e1e6")
        style.configure("Data.TLabel", font=("Consolas", 14, "bold"), foreground="#00e676")
        style.configure("BestData.TLabel", font=("Consolas", 14, "bold"), foreground="#00d2ff")

        self.build_ui()
        
        # Start the non-blocking polling sequence loop (checks every 500ms)
        self.check_for_new_laps()

    def build_ui(self):
        # Window Header
        lbl_header = ttk.Label(self.root, text="F1 TELEMETRY SESSION TRACKER", style="Header.TLabel", padding=10)
        lbl_header.pack()

        #Banner
        banner_frame = tk.Frame(root, bg='grey', height=40)
        banner_frame.pack_propagate(False)
        banner_frame.pack(fill=tk.X, side=tk.TOP)

        banner_text = tk.Label(banner_frame, text="Telemetry Inactive", fg="white", bg='red')
        ready_dir = Path(__file__).resolve().parent / "ready" / "ready.txt"
        banner_text.pack(expand=True)

        def check_telemetry():
            if ready_dir.exists() and is_game_running('f1_25.exe'):
                banner_text.config(
                    text="Telemetry Active",
                    bg="green"
                )
            else:
                banner_text.config(
                    text="Telemetry Inactive",
                    bg="red"
                )

            root.after(1000, check_telemetry)
        check_telemetry()

        # Main horizontal split layout container
        main_frame = tk.Frame(self.root, bg="#121214")
        main_frame.pack(fill="both", expand=True, padx=15, pady=5)

        # ================= LEFT COLUMN: LAST LAP COMPLETED =================
        left_panel = tk.LabelFrame(main_frame, text=" Last Completed Lap ", bg="#1f1f23", fg="#e1e1e6", font=("Arial", 10, "bold"), bd=1, padx=10, pady=10)
        left_panel.pack(side="left", fill="both", expand=True, padx=5)
        
        ttk.Label(left_panel, text="Lap Number:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_last_num = ttk.Label(left_panel, text="No Data", style="Data.TLabel")
        self.lbl_last_num.pack(anchor="w", pady=2)
        
        ttk.Label(left_panel, text="Final Lap Time:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_last_time = ttk.Label(left_panel, text="--:--.--", style="Data.TLabel")
        self.lbl_last_time.pack(anchor="w", pady=2)
        
        ttk.Label(left_panel, text="Top Speed Reached:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_last_speed = ttk.Label(left_panel, text="-- km/h", style="Data.TLabel")
        self.lbl_last_speed.pack(anchor="w", pady=2)
        
        ttk.Label(left_panel, text="Max Brake Input:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_last_brake = ttk.Label(left_panel, text="-- %", style="Data.TLabel")
        self.lbl_last_brake.pack(anchor="w", pady=2)

        # ================= RIGHT COLUMN: ALL-TIME SESSION BEST =================
        right_panel = tk.LabelFrame(main_frame, text=" Session Bench Record ", bg="#1f1f23", fg="#e1e1e6", font=("Arial", 10, "bold"), bd=1, padx=10, pady=10)
        right_panel.pack(side="right", fill="both", expand=True, padx=5)
        
        ttk.Label(right_panel, text="Lap Number:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_best_num = ttk.Label(right_panel, text="No Data", style="BestData.TLabel")
        self.lbl_best_num.pack(anchor="w", pady=2)
        
        ttk.Label(right_panel, text="Best Lap Time:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_best_time = ttk.Label(right_panel, text="--:--.--", style="BestData.TLabel")
        self.lbl_best_time.pack(anchor="w", pady=2)
        
        ttk.Label(right_panel, text="Top Speed Reached:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_best_speed = ttk.Label(right_panel, text="-- km/h", style="BestData.TLabel")
        self.lbl_best_speed.pack(anchor="w", pady=2)
        
        ttk.Label(right_panel, text="Max Brake Input:", style="MetricName.TLabel").pack(anchor="w", pady=2)
        self.lbl_best_brake = ttk.Label(right_panel, text="-- %", style="BestData.TLabel")
        self.lbl_best_brake.pack(anchor="w", pady=2)

        # Status Bar (Fixed with standard tk.Label syntax using padx/pady instead of padding)
        self.lbl_sys_status = tk.Label(self.root, text="System: Waiting for data files...", bg="#0a0a0c", fg="#a0a0a5", anchor="w", font=("Arial", 9, "italic"), padx=5, pady=5)
        self.lbl_sys_status.pack(fill="x", side="bottom")

    def format_lap_time(self, total_seconds):
        """Converts raw float seconds into a standard race display format MM:SS.ms"""
        try:
            total_seconds = float(total_seconds)
            minutes = int(total_seconds // 60)
            seconds = int(total_seconds % 60)
            milliseconds = int(round((total_seconds % 1) * 1000))
            return f"{minutes:02d}:{seconds:02d}.{milliseconds:03d}"
        except:
            return "--:--.--"

    def fetch_latest_file_from_dir(self, directory):
        """Returns the file path and modification timestamp of the newest file in a target folder."""
        files = glob.glob(os.path.join(directory, '*'))
        if not files:
            return None, 0.0
        newest_file = max(files, key=os.path.getmtime)
        return newest_file, os.path.getmtime(newest_file)

    def process_lap_dataframe(self, file_path):
        """Loads the newly exported CSV from your recorder and extracts dynamic peak statistics."""
        try:
            df = pd.read_csv(file_path)
            
            # Clean and ensure numeric formats exist
            for col in ['lap', 'lap_time', 'speed', 'brake']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')

            # Pull metrics safely matching your recorder's variable keys
            lap_number = int(df['lap'].dropna().iloc[-1]) if 'lap' in df.columns else "Unknown"
            final_time = df['lap_time'].dropna().iloc[-1] if 'lap_time' in df.columns else 0.0
            max_speed = df['speed'].max() if 'speed' in df.columns else 0.0
            
            # Scale brake pressure (your recorder prints float inputs, e.g., 0.0 to 1.0)
            max_brake = df['brake'].max() if 'brake' in df.columns else 0.0
            brake_pct = int(max_brake * 100) if max_brake <= 1.0 else int(max_brake)

            return {
                "lap": lap_number,
                "time": self.format_lap_time(final_time),
                "speed": f"{int(max_speed)} km/h",
                "brake": f"{brake_pct}%"
            }
        except Exception as e:
            return None

    def check_for_new_laps(self):
        """Monitors directories recursively for newly created session outputs."""
        # Check Last Lap directory
        recent_file, recent_mtime = self.fetch_latest_file_from_dir(self.last_lap_dir)
        if recent_file and recent_mtime > self.last_seen_recent_time:
            self.last_seen_recent_time = recent_mtime
            stats = self.process_lap_dataframe(recent_file)
            if stats:
                self.lbl_last_num.config(text=stats["lap"])
                self.lbl_last_time.config(text=stats["time"])
                self.lbl_last_speed.config(text=stats["speed"])
                self.lbl_last_brake.config(text=stats["brake"])
                self.lbl_sys_status.config(text=f"System: Loaded new lap update from {os.path.basename(recent_file)}", fg="#00e676")

        # Check Best Lap directory
        best_file, best_mtime = self.fetch_latest_file_from_dir(self.best_lap_dir)
        if best_file and best_mtime > self.last_seen_best_time:
            self.last_seen_best_time = best_mtime
            stats = self.process_lap_dataframe(best_file)
            if stats:
                self.lbl_best_num.config(text=stats["lap"])
                self.lbl_best_time.config(text=stats["time"])
                self.lbl_best_speed.config(text=stats["speed"])
                self.lbl_best_brake.config(text=stats["brake"])
                self.lbl_sys_status.config(text=f"System: New Record Bench Set! ({stats['time']})", fg="#00d2ff")

        # Re-schedule this method execution without causing interface blocking loops
        self.root.after(500, self.check_for_new_laps)

    def create_settings_window():
        settings_window = tk.Toplevel(root)
        settings_window.title("Settings")
        settings_window.geometry("300x200")


def run_reciever():
    global receiver_process
    # Use Popen instead of run() so it doesn't freeze the system thread
    receiver_process = subprocess.Popen([sys.executable, 'reciever.py'])

def onClose():
    print("Closing dashboard and stopping receiver...")
    
    # 1. Forcefully kill reciever.py if it is running
    global receiver_process
    if receiver_process and receiver_process.poll() is None: # checks if still running
        receiver_process.terminate()
        os.remove(Path(__file__).resolve().parent / "ready" / "ready.txt") # Sends termination signal
        # Optional: receiver_process.kill() # Use if terminate() isn't strong enough
    

        
    # 2. Safely destroy the GUI window
    root.destroy()


def is_game_running(game):
    for process in psutil.process_iter(['name']):
        try:
            # Check if the process name matches (case-insensitive)
            if process.info['name'] and game.lower() in process.info['name'].lower():
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            # Skip processes that closed or are protected by the OS
            continue
            
    return False


           
if __name__ == "__main__":
    root = tk.Tk()

    reciever_thread = threading.Thread(target=run_reciever, daemon=True)
    reciever_thread.start()
    
    # Simple check to make sure directory structures exist locally to prevent initial crash errors
    for folder in ['best_lap', 'last_lap']:
        if not os.path.exists(folder):
            os.makedirs(folder)
            
    app = F1LapTelemetryDashboard(root)
    root.protocol("WM_DELETE_WINDOW", onClose)
    root.mainloop()


