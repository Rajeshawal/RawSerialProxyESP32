import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import serial
import threading
from datetime import datetime
import csv
import re
import time

class ReceiverGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Receiver Only")

        self.input_ser = None
        self.running = False

        # --- Input Port Config ---
        ttk.Label(root, text="Input COM Port (e.g., COM10):").pack()
        self.port_entry = ttk.Entry(root)
        self.port_entry.pack()

        ttk.Label(root, text="Baudrate:").pack()
        self.baudrate_cb = ttk.Combobox(root, values=[9600, 19200, 38400, 57600, 115200], state="readonly")
        self.baudrate_cb.pack()
        self.baudrate_cb.set(9600)

        # --- Input Buttons ---
        button_frame = ttk.Frame(root)
        button_frame.pack(pady=5)
        self.connect_button = ttk.Button(button_frame, text="Connect Input", command=self.connect_input)
        self.connect_button.pack(side=tk.LEFT, padx=5)
        self.disconnect_button = ttk.Button(button_frame, text="Disconnect Input", command=self.disconnect_input, state="disabled")
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

        # --- Status
        self.status_label = ttk.Label(root, text="Status: Not Connected", foreground="red")
        self.status_label.pack()

        # --- Log Display
        ttk.Label(root, text="📥 Received Data").pack()
        self.recv_log = scrolledtext.ScrolledText(root, width=80, height=15, state='disabled')
        self.recv_log.pack(pady=5)

        # --- Log Controls
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=5)
        ttk.Button(control_frame, text="Clear Log", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Export Log to CSV", command=self.export_recv_csv).pack(side=tk.LEFT, padx=5)

    def connect_input(self):
        try:
            if self.input_ser and self.input_ser.is_open:
                self.update_log("[INFO] Input already connected")
                return
            in_port = self.port_entry.get().strip().upper()
            in_baud = int(self.baudrate_cb.get())
            self.input_ser = serial.Serial(in_port, in_baud, timeout=1)
            self.running = True
            self.status_label.config(text=f"Input Connected: {in_port}", foreground="green")
            self.disconnect_button.config(state="normal")
            threading.Thread(target=self.read_loop, daemon=True).start()
        except Exception as e:
            self.status_label.config(text=f"Input Connection Failed: {e}", foreground="red")

    def disconnect_input(self):
        try:
            self.running = False
            if self.input_ser and self.input_ser.is_open:
                self.input_ser.close()
            self.status_label.config(text="Input Disconnected", foreground="orange")
            self.disconnect_button.config(state="disabled")
        except Exception as e:
            self.status_label.config(text=f"Disconnection Error: {e}", foreground="red")

    def read_loop(self):
        while self.running:
            try:
                line = self.input_ser.readline().decode(errors='ignore').strip()
                if line:
                    timestamp = datetime.now().strftime("%H:%M:%S")
                    msg = f"[{timestamp}] {line}"
                    self.update_log(msg)
            except Exception as e:
                self.update_log(f"[ERROR] {e}")
            time.sleep(0.1)

    def update_log(self, message):
        self.recv_log.config(state='normal')
        self.recv_log.insert(tk.END, message + "\n")
        self.recv_log.yview(tk.END)
        self.recv_log.config(state='disabled')

    def clear_log(self):
        self.recv_log.config(state='normal')
        self.recv_log.delete(1.0, tk.END)
        self.recv_log.config(state='disabled')

    def export_recv_csv(self):
        lines = self.recv_log.get(1.0, tk.END).strip().splitlines()
        if not lines:
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", title="Save Log", filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            with open(path, mode='w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Time", "Sensor", "Stress", "ESP32_Timestamp"])
                for line in lines:
                    try:
                        time_label = re.search(r"\[(.*?)\]", line).group(1)
                        sensor = re.search(r"SENSOR=([^;]+)", line).group(1)
                        stress = re.search(r"STRESS=([^;\n]+)", line).group(1)
                        esp_time = re.search(r"TIME=([^;]+)", line).group(1)
                        writer.writerow([time_label, sensor, stress, esp_time])
                    except:
                        continue
            self.update_log(f"[INFO] Exported to {path}")
        except Exception as e:
            self.update_log(f"[ERROR] Export failed: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ReceiverGUI(root)
    root.mainloop()
