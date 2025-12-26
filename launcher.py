import tkinter as tk
from tkinter import font, messagebox, ttk
import subprocess
import platform
import threading
import queue
import json
import os
import datetime
import signal
from PIL import Image, ImageTk

# --- CẤU HÌNH ---
SETTINGS_FILE = "dashboard_config.json"
LOGO_FILENAME = "logo_ute.png"  # Đảm bảo file logo nằm cùng thư mục

DEFAULTS = {
    "host_ip": "0.0.0.0",
    "port": "8000",
    "yolo_model": "license_plate_detector.pt",
    "pi_ip": "192.168.1.16",
    "pi_user": "pi",
    "pc_ip": "192.168.1.112",  # IP máy tính chạy Dashboard này
    "camera_url": "0"          # Camera dùng cho Client
}

# --- GLOBAL VARS ---
log_queue = queue.Queue()
server_process = None
is_server_running = False

# --- UTILS ---
def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
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
    with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    return data

def run_terminal_cmd(cmd):
    sys_plat = platform.system()
    if sys_plat == "Windows":
        subprocess.Popen(f'start cmd /k "{cmd}"', shell=True)
    else:
        subprocess.Popen(f'gnome-terminal -- bash -c "{cmd}; exec bash"', shell=True)

# --- SERVER LOGIC (Chạy main.py Socket Server) ---
def server_thread():
    settings = save_settings()
    # Chạy main.py (Socket Server)
    cmd = [
        "python", "-u", "main.py",
        "--host", settings["host_ip"],
        "--port", settings["port"],
        "--model", settings["yolo_model"]
    ]
    
    global server_process
    try:
        startupinfo = None
        if platform.system() == 'Windows':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

        server_process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
            text=True, bufsize=1, encoding='utf-8', errors='ignore',
            startupinfo=startupinfo
        )
        log_queue.put("SYSTEM: Socket Server initialized. Waiting for connection...")
        
        while True:
            if server_process is None: break
            line = server_process.stdout.readline()
            if not line and server_process.poll() is not None: break
            if line: log_queue.put(line.strip())
            
    except Exception as e:
        log_queue.put(f"Server Error: {e}")

# --- CLIENT LOGIC (Gửi ảnh từ Camera tới Server) ---
def start_client():
    settings = save_settings()
    mode = nb_client.index(nb_client.select())
    
    target_ip = settings["pc_ip"]
    port = settings["port"]
    cam = settings["camera_url"]
    
    if mode == 0: # Local Client
        log_queue.put("SYSTEM: Starting Local Camera Client...")
        # Lưu ý: Bạn cần file pi_stream.py hoặc client.py ở cùng thư mục
        cmd = f'python pi_stream.py --server_ip "{target_ip}" --port {port} --camera "{cam}"'
        run_terminal_cmd(cmd)
    else: # Remote Pi
        pi_user = settings["pi_user"]
        pi_ip = settings["pi_ip"]
        log_queue.put(f"SYSTEM: Connecting to Pi {pi_ip}...")
        remote_cmd = f'python3 /home/{pi_user}/pi_stream.py --server_ip "{target_ip}" --port {port} --camera "{cam}"'
        ssh_cmd = f'ssh {pi_user}@{pi_ip} "{remote_cmd}"'
        run_terminal_cmd(ssh_cmd)

# --- DISPLAY LOGIC ---
def update_main_display(image_path):
    try:
        if os.path.exists(image_path):
            img = Image.open(image_path)
            
            w_frame = display_frame.winfo_width()
            h_frame = display_frame.winfo_height() - 80 
            if w_frame < 10 or h_frame < 10: return

            img_w, img_h = img.size
            ratio = min(w_frame/img_w, h_frame/img_h)
            new_w = int(img_w * ratio)
            new_h = int(img_h * ratio)
            
            img_resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            final_img = Image.new("RGB", (w_frame, h_frame), "black")
            final_img.paste(img_resized, ((w_frame-new_w)//2, (h_frame-new_h)//2))
            
            imgtk = ImageTk.PhotoImage(final_img)
            lbl_display_img.config(image=imgtk, text="")
            lbl_display_img.image = imgtk
    except Exception as e:
        pass

def gui_update_loop():
    try:
        while True:
            msg = log_queue.get_nowait()
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            
            # --- PARSE LOG TỪ SOCKET SERVER (main.py cũ) ---
            # main.py cũ in ra: "PLATE FOUND: 59P1..."
            if "PLATE FOUND:" in msg:
                plate_text = msg.split("PLATE FOUND:")[1].strip()
                lbl_result_text.config(text=plate_text, fg="#00ff00") 
                lbl_status.config(text="ACCESS GRANTED", fg="#00ff00") 
                txt_log.insert(tk.END, f"[{timestamp}] DETECTED: {plate_text}\n")
                txt_log.see(tk.END)
            
            # main.py cũ in ra: "SAVED detected_plates/..."
            elif "SAVED " in msg:
                img_path = msg.split("SAVED ")[1].strip()
                update_main_display(img_path)
            
            else:
                txt_log.insert(tk.END, f"[{timestamp}] {msg}\n")
                txt_log.see(tk.END)

    except queue.Empty:
        pass
    root.after(100, gui_update_loop)

# --- START/STOP SERVER ---
def toggle_server():
    global is_server_running
    if not is_server_running:
        start_server()
    else:
        stop_server()

def start_server():
    global is_server_running
    save_settings()
    is_server_running = True
    btn_server.config(text="STOP SERVER", bg="#d9534f")
    lbl_status.config(text="LISTENING...", fg="yellow")
    t = threading.Thread(target=server_thread, daemon=True)
    t.start()

def stop_server():
    global server_process, is_server_running
    if server_process:
        try:
            if platform.system() == 'Windows':
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(server_process.pid)])
            else:
                os.kill(server_process.pid, signal.SIGTERM)
        except: pass
    server_process = None
    is_server_running = False
    btn_server.config(text="START SERVER", bg="#007acc")
    lbl_status.config(text="SERVER STOPPED", fg="red")
    lbl_display_img.config(image="", text="NO SIGNAL")
    log_queue.put("SYSTEM: Server stopped.")

def toggle_fullscreen(event=None):
    root.attributes('-fullscreen', not root.attributes('-fullscreen'))

# --- GUI SETUP ---
root = tk.Tk()
root.title("LPR SOCKET SYSTEM - TEAM CPR")
root.geometry("1280x800")
root.configure(bg="#1e1e1e")
root.bind("<F11>", toggle_fullscreen)

STYLE_BG = "#1e1e1e"
STYLE_PANEL = "#252526"
STYLE_HEADER = "#003366"
FONT_BOLD = ("Segoe UI", 10, "bold")

# === LAYOUT ===
root.grid_rowconfigure(0, weight=0) 
root.grid_rowconfigure(1, weight=1) 
root.grid_columnconfigure(0, weight=1)

# 1. HEADER
header = tk.Frame(root, bg=STYLE_HEADER, pady=5, padx=10)
header.grid(row=0, column=0, sticky="ew")

# Logo
logo_frame = tk.Frame(header, bg=STYLE_HEADER)
logo_frame.pack(side="left", padx=(0, 15))
current_dir = os.getcwd()
logo_path_full = os.path.join(current_dir, LOGO_FILENAME)
try:
    if os.path.exists(logo_path_full):
        orig_logo = Image.open(logo_path_full)
        orig_logo.thumbnail((70, 70), Image.Resampling.LANCZOS)
        logo_tk = ImageTk.PhotoImage(orig_logo)
        lbl_logo = tk.Label(logo_frame, image=logo_tk, bg=STYLE_HEADER)
        lbl_logo.image = logo_tk
        lbl_logo.pack()
    else:
        tk.Label(logo_frame, text="[LOGO UTE]", bg=STYLE_HEADER, fg="white", font=("Arial", 12, "bold")).pack()
except: pass

# Title
title_frame = tk.Frame(header, bg=STYLE_HEADER)
title_frame.pack(side="left")
tk.Label(title_frame, text="LICENSE PLATE DETECTION SYSTEM", bg=STYLE_HEADER, fg="white", font=("Segoe UI", 16, "bold")).pack(anchor="w")
tk.Label(title_frame, text="Nguyễn Ngọc Gia Nguyễn - 23110046 | Nguyễn Hằng Hải Long - 23110036 | Trần Hữu Đức - 23110018", bg=STYLE_HEADER, fg="#ddd", font=("Segoe UI", 9)).pack(anchor="w")

# 2. BODY
body = tk.Frame(root, bg=STYLE_BG)
body.grid(row=1, column=0, sticky="nsew")
body.grid_columnconfigure(1, weight=1)
body.grid_rowconfigure(0, weight=1)

# SIDEBAR (SETTINGS + CLIENT)
sidebar = tk.Frame(body, bg=STYLE_PANEL, width=280, padx=10, pady=10)
sidebar.grid(row=0, column=0, sticky="ns")
sidebar.pack_propagate(False)

# Settings
tk.Label(sidebar, text="SERVER CONFIG", font=("Segoe UI", 11, "bold"), bg=STYLE_PANEL, fg="white").pack(pady=(0,5))
def add_entry(p, lbl, k):
    tk.Label(p, text=lbl, bg=STYLE_PANEL, fg="#ccc", font=("Segoe UI", 9)).pack(anchor="w")
    e = tk.Entry(p, bg="#333", fg="white", relief="flat"); e.insert(0, load_settings().get(k,"")); e.pack(fill="x", pady=(0, 5))
    return e
ent_host = add_entry(sidebar, "Host IP", "host_ip")
ent_port = add_entry(sidebar, "Port", "port")
ent_model = add_entry(sidebar, "Model", "yolo_model")

# Client Controls (Để kết nối Camera)
tk.Label(sidebar, text="CLIENT CONNECTION", font=("Segoe UI", 11, "bold"), bg=STYLE_PANEL, fg="#00aaff").pack(pady=(20,5))
ent_pc_ip = add_entry(sidebar, "Server IP (My PC)", "pc_ip")
ent_cam = add_entry(sidebar, "Camera Source", "camera_url")

nb_client = ttk.Notebook(sidebar); nb_client.pack(fill="x", pady=5)
t_local = tk.Frame(nb_client, bg=STYLE_PANEL); nb_client.add(t_local, text="Local")
t_remote = tk.Frame(nb_client, bg=STYLE_PANEL); nb_client.add(t_remote, text="SSH Pi")
ent_pi_ip = add_entry(t_remote, "Pi IP", "pi_ip")
ent_pi_user = add_entry(t_remote, "User", "pi_user")

# Nút bật Client
btn_client = tk.Button(sidebar, text="CONNECT CAMERA", bg="#28a745", fg="white", font=FONT_BOLD, command=start_client)
btn_client.pack(fill="x", pady=10)

# MAIN CONTENT
main_content = tk.Frame(body, bg=STYLE_BG, padx=10, pady=10)
main_content.grid(row=0, column=1, sticky="nsew")
main_content.grid_columnconfigure(0, weight=1)
main_content.grid_rowconfigure(0, weight=4) 
main_content.grid_rowconfigure(1, weight=1) 

# DISPLAY AREA
display_frame = tk.Frame(main_content, bg="black", bd=2, relief="sunken")
display_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 5))

lbl_display_img = tk.Label(display_frame, text="NO SIGNAL", bg="black", fg="#333", font=("Arial", 24, "bold"))
lbl_display_img.pack(fill="both", expand=True)

result_container = tk.Frame(display_frame, bg="#111", height=80)
result_container.pack(side="bottom", fill="x")
result_container.pack_propagate(False)

lbl_status = tk.Label(result_container, text="SYSTEM READY - WAITING FOR CONNECTION", fg="#888", bg="#111", font=("Consolas", 10))
lbl_status.pack(side="top", pady=(5,0))
lbl_result_text = tk.Label(result_container, text="---", bg="#111", fg="#00ff00", font=("Consolas", 32, "bold"))
lbl_result_text.pack(side="top")

# LOGS & SERVER CONTROL
bottom_frame = tk.Frame(main_content, bg=STYLE_BG)
bottom_frame.grid(row=1, column=0, sticky="nsew")
bottom_frame.grid_columnconfigure(1, weight=1)

btn_frame = tk.Frame(bottom_frame, bg=STYLE_BG, width=150)
btn_frame.grid(row=0, column=0, sticky="ns", padx=(0, 5))
btn_server = tk.Button(btn_frame, text="START SERVER", bg="#007acc", fg="white", font=FONT_BOLD, command=toggle_server)
btn_server.pack(fill="both", expand=True)

log_box = tk.Frame(bottom_frame, bg="black")
log_box.grid(row=0, column=1, sticky="nsew")
txt_log = tk.Text(log_box, bg="#111", fg="#00ff00", font=("Consolas", 9), bd=0)
txt_log.pack(fill="both", expand=True)

root.after(100, gui_update_loop)
root.mainloop()