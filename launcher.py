import tkinter as tk
from tkinter import font, messagebox
import subprocess
import platform
import threading
import queue
import json
import os
SETTINGS_FILE = "dashboard_config.json"
DEFAULTS = {
    "host_ip": "0.0.0.0",
    "port": "8000",
    "yolo_model": "license_plate_detector.pt",
    "pi_ip": "192.168.82.16",
    "pi_user": "pi",
    "pc_ip": "192.168.131.16",
    "camera_url": "http://192.168.131.105:8080/video"
}

log_queue = queue.Queue()
server_process = None
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return DEFAULTS.copy()

def save_settings():
    data = {
        "host_ip": ent_host.get(),
        "port": ent_port.get(),
        "yolo_model": ent_model.get(),
        "pi_ip": ent_pi_ip.get(),
        "pi_user": ent_pi_user.get(),
        "pc_ip": ent_pc_ip.get(),
        "camera_url": ent_cam.get()
    }
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(data, f, indent=4)
    return data

def run_terminal_cmd(cmd):
    sys_plat = platform.system()
    if sys_plat == "Windows":
        subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
    elif sys_plat == "Darwin":
        subprocess.Popen(['open', '-a', 'Terminal', cmd])
    else:
        subprocess.Popen(f'gnome-terminal -- bash -c "{cmd}; exec bash"', shell=True)
def server_thread():
    settings = save_settings()
    cmd = [
        "python", "-u", "main.py",
        "--host", settings["host_ip"],
        "--port", settings["port"],
        "--model", settings["yolo_model"]
    ]
    
    global server_process
    try:
        flags = subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
        server_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            text=True, bufsize=1, creationflags=flags
        )
        while True:
            line = server_process.stdout.readline()
            if not line and server_process.poll() is not None: break
            if line: log_queue.put(line.strip())
            
    except Exception as e:
        log_queue.put(f"Server failed: {e}")

def gui_update_loop():
    try:
        while True:
            msg = log_queue.get_nowait()
            txt_log.insert(tk.END, f"{msg}\n")
            txt_log.see(tk.END)
            
            if "PLATE:" in msg:
                plate = msg.split("PLATE:")[1].strip()
                lbl_plate.config(text=plate, fg="#00ff00")
                
    except queue.Empty:
        pass
    root.after(100, gui_update_loop)
def on_start_server():
    save_settings()
    btn_server.config(state="disabled", text="Server Running...", bg="#444")
    t = threading.Thread(target=server_thread, daemon=True)
    t.start()

def on_start_client():
    settings = save_settings()
    mode = nb_client.index(nb_client.select())
    
    target_ip = settings["pc_ip"]
    port = settings["port"]
    cam = settings["camera_url"]
    
    if mode == 0:
        print("Starting Local Client...")
        cmd = f'python pi_stream.py --server_ip "{target_ip}" --port {port} --camera "{cam}"'
        run_terminal_cmd(cmd)
        
    else:
        pi_user = settings["pi_user"]
        pi_ip = settings["pi_ip"]
        print(f" SSH to Pi {pi_ip}...")
        remote_cmd = f'python3 /home/{pi_user}/pi_stream.py --server_ip "{target_ip}" --port {port} --camera "{cam}"'
        ssh_cmd = f'ssh {pi_user}@{pi_ip} "{remote_cmd}"'
        run_terminal_cmd(ssh_cmd)

root = tk.Tk()
root.title("LPR Command Center")
root.geometry("800x600")
root.configure(bg="#1e1e1e")

style_font = ("Segoe UI", 10)
style_bg = "#1e1e1e"
style_fg = "#ffffff"
tk.Label(root, text="License Plate Recognition System", font=("Segoe UI", 18, "bold"), bg=style_bg, fg="#00aaff").pack(pady=15)
main_frame = tk.Frame(root, bg=style_bg)
main_frame.pack(fill="both", expand=True, padx=20)
left_col = tk.Frame(main_frame, bg=style_bg)
left_col.pack(side="left", fill="both", expand=True)

def add_entry(parent, label, key):
    tk.Label(parent, text=label, bg=style_bg, fg="gray", font=("Segoe UI", 9)).pack(anchor="w", pady=(5,0))
    ent = tk.Entry(parent, bg="#333", fg="white", insertbackground="white", relief="flat")
    ent.insert(0, saved_settings.get(key, ""))
    ent.pack(fill="x", pady=2, ipady=3)
    return ent

saved_settings = load_settings()

tk.Label(left_col, text="SERVER CONFIG", bg=style_bg, fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(10,5))
ent_host = add_entry(left_col, "Host IP (0.0.0.0 default)", "host_ip")
ent_port = add_entry(left_col, "Port", "port")
ent_model = add_entry(left_col, "YOLO Model Path", "yolo_model")
ent_pc_ip = add_entry(left_col, "YOUR PC IP", "pc_ip")

tk.Label(left_col, text="CLIENT CONFIG", bg=style_bg, fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(20,5))
ent_cam = add_entry(left_col, "Camera Source (URL or 0)", "camera_url")
from tkinter import ttk
style = ttk.Style()
style.theme_use('clam')
style.configure("TNotebook", background=style_bg, borderwidth=0)
style.configure("TNotebook.Tab", background="#333", foreground="white", borderwidth=0)
style.map("TNotebook.Tab", background=[("selected", "#007acc")])

nb_client = ttk.Notebook(left_col)
nb_client.pack(fill="x", pady=10)

tab_local = tk.Frame(nb_client, bg=style_bg)
tab_remote = tk.Frame(nb_client, bg=style_bg)

nb_client.add(tab_local, text=" Local Mode ")
nb_client.add(tab_remote, text=" Remote Pi Mode ")

ent_pi_ip = add_entry(tab_remote, "Pi IP Address", "pi_ip")
ent_pi_user = add_entry(tab_remote, "Pi Username", "pi_user") 
tk.Label(tab_local, text="Runs 'pi_stream.py' on this computer.", bg=style_bg, fg="gray").pack(pady=10)

right_col = tk.Frame(main_frame, bg=style_bg)
right_col.pack(side="right", fill="both", expand=True, padx=(20,0))

res_frame = tk.Frame(right_col, bg="#252526", bd=1, relief="solid")
res_frame.pack(fill="x", pady=(28, 10))
tk.Label(res_frame, text="LATEST PLATE", bg="#252526", fg="gray", font=("Arial", 8)).pack()
lbl_plate = tk.Label(res_frame, text="---", bg="#252526", fg="white", font=("Consolas", 36, "bold"))
lbl_plate.pack(pady=10)

btn_server = tk.Button(right_col, text="START SERVER", bg="#007acc", fg="white", font=("Segoe UI", 10, "bold"), height=2, relief="flat", command=on_start_server)
btn_server.pack(fill="x", pady=5)

btn_client = tk.Button(right_col, text="START CAMERA STREAM", bg="#ffffff", fg="white", font=("Segoe UI", 10, "bold"), height=2, relief="flat", command=on_start_client)
btn_client.pack(fill="x", pady=5)

# Logs
tk.Label(right_col, text="System Logs", bg=style_bg, fg="gray").pack(anchor="w", pady=(10,0))
txt_log = tk.Text(right_col, bg="black", fg="#ffffff", font=("Consolas", 9), height=15, bd=0)
txt_log.pack(fill="both", expand=True)

root.after(100, gui_update_loop)
root.mainloop()