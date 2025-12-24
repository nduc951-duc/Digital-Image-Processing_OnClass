import tkinter as tk
from tkinter import font
import subprocess
import platform
import threading
import queue
USE_LOCAL_MODE = True 
SERVER_SCRIPT = "D:\\College\\_hk5\\DIPR\\raspibackup\\main_pipeline\\main.py"
CLIENT_SCRIPT = "D:\\College\\_hk5\\DIPR\\raspibackup\\main_pipeline\\pi_stream.py" 
PI_USER = "pi"
PI_IP = "192.168.82.16"
PI_REMOTE_PATH = "/home/pi/pi_stream.py"
log_queue = queue.Queue()

def run_in_terminal(command):
    """Launches external terminals (Used for the Client/Pi only)"""
    system = platform.system()
    if system == "Windows":
        subprocess.Popen(f'start cmd /k "{command}"', shell=True)
    elif system == "Darwin":
        subprocess.Popen(['open', '-a', 'Terminal', command]) 
    else:
        try:
            subprocess.Popen(f'xterm -e "{command}"', shell=True)
        except:
            subprocess.Popen(f'gnome-terminal -- bash -c "{command}; exec bash"', shell=True)

def server_thread_func():
    cmd = ["python", "-u", SERVER_SCRIPT] 
    
    try:
        process = subprocess.Popen(
            cmd, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            bufsize=1,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        )
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                log_queue.put(line.strip())
                
    except Exception as e:
        log_queue.put(f"[ERROR] Could not start server: {e}")

def update_gui_from_queue():
    try:
        while True:
            msg = log_queue.get_nowait()
            txt_log.insert(tk.END, msg + "\n")
            txt_log.see(tk.END)
            if "PLATE:" in msg:
                plate_text = msg.split("PLATE:")[1].strip()
                lbl_result.config(text=plate_text, fg="#ffffff")
                
    except queue.Empty:
        pass
    root.after(100, update_gui_from_queue)

def start_server():
    print("[UI] Launching Server (Internal Mode)...")
    btn_server.config(state="disabled", text="Server Running...", bg="gray")
    t = threading.Thread(target=server_thread_func, daemon=True)
    t.start()

def start_client():
    if USE_LOCAL_MODE:
        print("[UI] Launching Client (LOCAL SIMULATION)...")
        run_in_terminal(f"python {CLIENT_SCRIPT}")
    else:
        print(f"[UI] Launching Client (REMOTE PI @ {PI_IP})...")
        ssh_cmd = f'ssh {PI_USER}@{PI_IP} "python3 {PI_REMOTE_PATH}"'
        run_in_terminal(ssh_cmd)
root = tk.Tk()
root.title("LPR System Controller")
root.geometry("500x450")
root.configure(bg="#1e1e1e")
header_font = font.Font(family="Arial", size=16, weight="bold")
result_font = font.Font(family="Courier New", size=30, weight="bold")
tk.Label(root, text="LPR Dashboard", font=header_font, bg="#1e1e1e", fg="white").pack(pady=10)
frame_result = tk.Frame(root, bg="#333", bd=2, relief="sunken")
frame_result.pack(fill="x", padx=20, pady=5)

tk.Label(frame_result, text="LATEST DETECTED PLATE:", bg="#333", fg="gray", font=("Arial", 10)).pack(pady=5)
lbl_result = tk.Label(frame_result, text="---", bg="#333", fg="white", font=result_font)
lbl_result.pack(pady=10)
frame_controls = tk.Frame(root, bg="#1e1e1e")
frame_controls.pack(fill="x", padx=20, pady=10)

btn_server = tk.Button(frame_controls, text="1. Start Server", 
                       bg="#add8e6", font=("Arial", 11), height=2, 
                       command=start_server)
btn_server.pack(side="left", fill="x", expand=True, padx=5)

btn_text = "2. Start Client" if USE_LOCAL_MODE else "2. Start Client"
client_color = "#FFFF00" if USE_LOCAL_MODE else "#90ee90"
btn_pi = tk.Button(frame_controls, text=btn_text, 
                   bg=client_color, font=("Arial", 11), height=2, 
                   command=start_client)
btn_pi.pack(side="right", fill="x", expand=True, padx=5)
tk.Label(root, text="System Logs:", bg="#1e1e1e", fg="gray").pack(anchor="w", padx=20)
txt_log = tk.Text(root, height=8, bg="black", fg="#ffffff", font=("Consolas", 9))
txt_log.pack(fill="both", expand=True, padx=20, pady=(0, 20))
root.after(100, update_gui_from_queue)
root.mainloop()