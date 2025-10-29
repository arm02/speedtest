"""
ui_speedtest_full.py

Aplikasi desktop sederhana untuk speed test (Windows)
Fitur:
- Tombol Start Test
- Dropdown pilih server (Auto + daftar server)
- Grafik history (download & upload) yang ditampilkan di window
- Simpan history ke CSV
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
import csv

# external libs
import speedtest
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# -----------------------
# Helper / Global state
# -----------------------
st_global = None  # shared Speedtest object
servers_map = {}  # mapping display -> server_id (string->int)
history = []  # list of tuples (timestamp_str, download_mbps, upload_mbps, ping_ms)

# -----------------------
# Core Speedtest functions
# -----------------------
def create_speedtest_instance():
    global st_global
    try:
        st_global = speedtest.Speedtest()
    except Exception as e:
        st_global = None
        raise

def fetch_and_populate_servers(combobox, status_label, max_entries=40):
    """
    Ambil server list dari speedtest.net (non-blocking caller)
    Isi combobox dengan "Auto" + daftar server teratas berdasarkan jarak
    """
    def worker():
        try:
            status_label.config(text="Loading server list...")
            create_speedtest_instance()
            # get_servers will populate st_global.servers
            st_global.get_servers()  # fetch servers
            # st_global.servers is dict: keys = host/ip? values = list of server dicts
            servers = []
            for k, lst in (st_global.servers or {}).items():
                for s in lst:
                    # collect relevant info safely
                    sid = s.get("id") or s.get("server")
                    sponsor = s.get("sponsor") or s.get("sponsor", "")
                    name = s.get("name") or s.get("name", "")
                    country = s.get("country") or s.get("country", "")
                    # distance might be 'd' or 'distance'
                    distance = s.get("d") or s.get("distance") or s.get("dist") or ""
                    try:
                        distance_val = float(distance)
                    except Exception:
                        distance_val = float("inf")
                    servers.append({
                        "id": sid,
                        "sponsor": sponsor,
                        "name": name,
                        "country": country,
                        "distance": distance_val
                    })
            # sort by distance
            servers_sorted = sorted(servers, key=lambda x: (x["distance"] is None, x["distance"]))
            # prepare display strings and mapping
            display_list = ["Auto"]
            local_map = {}
            count = 0
            for s in servers_sorted:
                if count >= max_entries:
                    break
                sid = s["id"]
                # make display friendly
                disp = f'{sid} | {s["sponsor"]} ({s["name"]}, {s["country"]})'
                display_list.append(disp)
                local_map[disp] = sid
                count += 1

            # update UI on main thread
            def ui_update():
                servers_map.clear()
                servers_map.update(local_map)
                combobox["values"] = display_list
                combobox.set("Auto")
                status_label.config(text=f"Loaded {len(display_list)-1} servers (closest).")
            root.after(0, ui_update)
        except Exception as e:
            def fail_update():
                combobox["values"] = ["Auto"]
                combobox.set("Auto")
                status_label.config(text=f"Failed to load servers: {e}")
            root.after(0, fail_update)

    threading.Thread(target=worker, daemon=True).start()

def run_speedtest(selected_display, status_label, result_text_widget, btn_start):
    """
    Jalankan speedtest pada thread terpisah.
    selected_display: combobox value (string) - "Auto" atau display string yang dipetakan ke server id
    """
    def worker():
        nonlocal selected_display
        try:
            btn_start.config(state="disabled")
            status_label.config(text="Running speedtest... This may take 20-40s depending on server.")
            # create instance if not exist
            if st_global is None:
                create_speedtest_instance()

            st = st_global

            # pick server
            if selected_display != "Auto" and selected_display in servers_map:
                sid = servers_map[selected_display]
                try:
                    # request only that server
                    st.get_servers([int(sid)])
                except Exception:
                    # fallback: try by string id
                    try:
                        st.get_servers([sid])
                    except Exception:
                        pass
                # get_best_server will choose among provided servers
                best = st.get_best_server()
            else:
                st.get_servers()
                best = st.get_best_server()

            # Show chosen server
            chosen = best or {}
            server_info = f"Using server: {chosen.get('sponsor','?')} ({chosen.get('name','?')}, {chosen.get('country','?')})\n"
            def ui_show_server():
                result_text_widget.config(state="normal")
                result_text_widget.delete("1.0", tk.END)
                result_text_widget.insert(tk.END, server_info + "Testing download...\n")
                result_text_widget.config(state="disabled")
            root.after(0, ui_show_server)

            # download & upload
            download_bps = st.download()
            upload_bps = st.upload()
            ping_ms = st.results.ping if hasattr(st, "results") and getattr(st, "results") else (st.results.ping if hasattr(st, "results") else None)

            download_mbps = download_bps / 1_000_000
            upload_mbps = upload_bps / 1_000_000
            ping_ms = ping_ms or 0.0

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # append to history
            history.append((timestamp, download_mbps, upload_mbps, ping_ms))

            # update UI with results
            def ui_update_result():
                txt = (
                    f"{server_info}"
                    f"Download : {download_mbps:.2f} Mbps\n"
                    f"Upload   : {upload_mbps:.2f} Mbps\n"
                    f"Ping     : {ping_ms:.2f} ms\n"
                    f"Time     : {timestamp}\n"
                )
                result_text_widget.config(state="normal")
                result_text_widget.delete("1.0", tk.END)
                result_text_widget.insert(tk.END, txt)
                result_text_widget.config(state="disabled")
                status_label.config(text="Done.")
                btn_start.config(state="normal")
                update_plot()
            root.after(0, ui_update_result)

        except Exception as e:
            def ui_err():
                messagebox.showerror("Error", f"Speedtest failed: {e}")
                status_label.config(text=f"Error: {e}")
                btn_start.config(state="normal")
            root.after(0, ui_err)

    threading.Thread(target=worker, daemon=True).start()

# -----------------------
# Plotting (matplotlib in Tk)
# -----------------------
fig = Figure(figsize=(6,3), dpi=100)
ax = fig.add_subplot(111)
ax.set_title("Speed History")
ax.set_xlabel("Time")
ax.set_ylabel("Mbps")
line_dl, = ax.plot([], [], label="Download")
line_ul, = ax.plot([], [], label="Upload")
ax.legend()
ax.grid(True)
canvas = None  # will be set when embedding

def update_plot():
    times = [h[0].split(" ")[1] for h in history]  # show only HH:MM:SS
    downloads = [round(h[1], 2) for h in history]
    uploads = [round(h[2], 2) for h in history]
    ax.clear()
    ax.plot(times, downloads, marker='o', label="Download")
    ax.plot(times, uploads, marker='o', label="Upload")
    ax.set_title("Speed History")
    ax.set_xlabel("Time")
    ax.set_ylabel("Mbps")
    ax.legend()
    ax.grid(True)
    fig.tight_layout()
    if canvas:
        canvas.draw()

# -----------------------
# Save history to CSV
# -----------------------
def save_history_to_csv():
    if not history:
        messagebox.showinfo("Info", "Belum ada history untuk disimpan.")
        return
    fname = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files","*.csv")], title="Save history as...")
    if not fname:
        return
    try:
        with open(fname, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp","download_mbps","upload_mbps","ping_ms"])
            for row in history:
                writer.writerow(row)
        messagebox.showinfo("Saved", f"History disimpan ke {fname}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal menyimpan: {e}")

# -----------------------
# Build Tkinter UI
# -----------------------
root = tk.Tk()
root.title("My Internet Speed Test")
root.geometry("780x480")

# left frame = controls
left = ttk.Frame(root, padding=(10,10))
left.pack(side=tk.LEFT, fill=tk.Y)

ttk.Label(left, text="Internet Speed Test", font=("Segoe UI", 14, "bold")).pack(pady=(0,10))

status_label = ttk.Label(left, text="Ready", wraplength=220)
status_label.pack(pady=(0,8))

# server dropdown
ttk.Label(left, text="Pilih Server (Auto atau pilih manual):").pack(anchor="w")
server_var = tk.StringVar(value="Auto")
server_dropdown = ttk.Combobox(left, textvariable=server_var, values=["Auto"], width=40)
server_dropdown.pack(pady=(0,8))

load_button = ttk.Button(left, text="Load Server List (may take 10-30s)", command=lambda: fetch_and_populate_servers(server_dropdown, status_label, max_entries=50))
load_button.pack(fill="x", pady=(0,8))

# start button
start_button = ttk.Button(left, text="Start Test", command=lambda: run_speedtest(server_var.get(), status_label, result_text, start_button))
start_button.pack(fill="x", pady=(2,8))

# save button
save_button = ttk.Button(left, text="Save History to CSV", command=save_history_to_csv)
save_button.pack(fill="x", pady=(2,8))

# result text
ttk.Label(left, text="Result:").pack(anchor="w", pady=(8,0))
result_text = tk.Text(left, width=45, height=10, state="disabled", wrap="word")
result_text.pack(pady=(0,8))

# right frame = plot
right = ttk.Frame(root, padding=(10,10))
right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

# embed matplotlib canvas
canvas = FigureCanvasTkAgg(fig, master=right)
canvas_widget = canvas.get_tk_widget()
canvas_widget.pack(fill=tk.BOTH, expand=True)

# small tips
tips = ttk.Label(right, text="Tips: Klik 'Load Server List' lalu pilih server yang diinginkan.\n'Auto' akan memilih server terbaik otomatis.", justify="left")
tips.pack(anchor="w", pady=(6,0), padx=(6,0))

# initialize: draw empty plot
update_plot()

# On start, try to create speedtest instance in background to speed up later tests
def warmup():
    try:
        create_speedtest_instance()
        status_label.config(text="Speedtest engine ready. Click 'Load Server List' to fetch servers.")
    except Exception as e:
        status_label.config(text=f"Engine init failed: {e}")
threading.Thread(target=warmup, daemon=True).start()

# start UI loop
root.mainloop()
