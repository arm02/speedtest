import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime
import speedtest
import math

# --- Speedometer Draw Config ---
WIDTH = 350
HEIGHT = 350
CENTER = (WIDTH//2, HEIGHT//2)
RADIUS = 140

MAX_SPEED = 200  # Target speed max (Mbps) — bisa kamu sesuaikan

# create UI window
root = tk.Tk()
root.title("Speed Test Speedometer")
root.geometry("400x500")
root.resizable(False, False)

canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="black")
canvas.pack(pady=(10,10))

speed_label = ttk.Label(root, text="0.00 Mbps", font=("Segoe UI", 18, "bold"))
speed_label.pack(pady=5)

start_button = ttk.Button(root, text="Start Test")
start_button.pack(fill="x", padx=20, pady=10)

status_label = ttk.Label(root, text="Ready", font=("Segoe UI", 10))
status_label.pack()

# --- Draw speedometer scale ---
def draw_gauge():
    canvas.delete("all")

    # arc background
    canvas.create_arc(20,20,WIDTH-20,HEIGHT-20, start=135, extent=270,
                      outline="#202020", width=25, style=tk.ARC)

    # scale ticks
    for i in range(0, 201, 25):
        angle = 135 + (i / MAX_SPEED) * 270
        rad = math.radians(angle)
        x1 = CENTER[0] + (RADIUS-25)*math.cos(rad)
        y1 = CENTER[1] + (RADIUS-25)*math.sin(rad)
        x2 = CENTER[0] + RADIUS*math.cos(rad)
        y2 = CENTER[1] + RADIUS*math.sin(rad)
        canvas.create_line(x1, y1, x2, y2, fill="gray", width=3)

    # Zero needle initial
    draw_needle(0)

def draw_needle(speed):
    angle = 135 + (speed / MAX_SPEED) * 270
    rad = math.radians(angle)
    x = CENTER[0] + (RADIUS-30)*math.cos(rad)
    y = CENTER[1] + (RADIUS-30)*math.sin(rad)

    canvas.delete("needle")
    canvas.create_line(CENTER[0], CENTER[1], x, y,
                       fill="red", width=4, tags="needle")
    canvas.create_oval(CENTER[0]-8, CENTER[1]-8,
                       CENTER[0]+8, CENTER[1]+8,
                       fill="white", outline="", tags="needle")

draw_gauge()

# --- Animated smooth needle update ---
def animate_speed(target_speed):
    current = 0.0
    step = (target_speed - current) / 50

    for i in range(50):
        current += step
        draw_needle(current)
        speed_label.config(text=f"{current:.2f} Mbps")
        root.update()
        time.sleep(0.02)

    draw_needle(target_speed)
    speed_label.config(text=f"{target_speed:.2f} Mbps")


# --- Speedtest Runner ---
def run_speedtest():
    start_button.config(state="disabled")
    status_label.config(text="Finding best server...")

    try:
        st = speedtest.Speedtest()
        st.get_servers()
        st.get_best_server()

        status_label.config(text="Testing download speed...")
        root.update()

        # download test with live animation
        dl_bps = st.download()
        dl_mbps = dl_bps / 1_000_000
        animate_speed(min(dl_mbps, MAX_SPEED))

        status_label.config(text="Testing upload speed...")
        root.update()

        time.sleep(0.5)
        animate_speed(0)  # reset animation quick

        ul_bps = st.upload()
        ul_mbps = ul_bps / 1_000_000
        animate_speed(min(ul_mbps, MAX_SPEED))

        ping = st.results.ping if hasattr(st.results, "ping") else 0

        messagebox.showinfo("Speedtest Result",
                            f"Download: {dl_mbps:.2f} Mbps\n"
                            f"Upload: {ul_mbps:.2f} Mbps\n"
                            f"Ping: {ping:.0f} ms")

        status_label.config(text="Done ✅")

    except Exception as e:
        messagebox.showerror("Error", str(e))
        status_label.config(text="Failed ❌")

    start_button.config(state="normal")

def thread_speedtest():
    threading.Thread(target=run_speedtest, daemon=True).start()

start_button.config(command=thread_speedtest)

root.mainloop()
