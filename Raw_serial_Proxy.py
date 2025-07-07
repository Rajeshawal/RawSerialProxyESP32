import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import serial
import threading
import csv
from datetime import datetime
import os

def parse_serial_line(line: str):
    """Parses serial line into (sensor, stress, time)"""
    try:
        fields = dict(part.split('=') for part in line.split(';') if '=' in part)
        sensor = fields.get("SENSOR", "N/A")
        stress = fields.get("STRESS", "N/A")
        timestamp = fields.get("TIME", "N/A")
        return sensor, stress, timestamp
    except Exception:
        return "N/A", "N/A", "N/A"

class SerialProxyGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Serial Proxy Receiver + Forwarder")
        self.root.geometry("900x600")

        self.input_ser = None
        self.output_ser = None
        self.running = False

        self.input_csv_file = None
        self.forwarded_csv_file = None
        self.input_csv_writer = None
        self.forwarded_csv_writer = None

        layout_frame = ttk.Frame(root)
        layout_frame.pack(pady=10, fill='x')  # Add fill for better stretching

        # === Input ===
        input_frame = ttk.LabelFrame(layout_frame, text="Input Configuration")
        input_frame.grid(row=0, column=0, padx=(40, 255), sticky="n")  # Increased left and right padding    

        ttk.Label(input_frame, text="Input COM Port:(e.g., COM5)").grid(row=0, column=0, sticky="w")
        self.input_port_entry = ttk.Entry(input_frame)
        self.input_port_entry.grid(row=1, column=0, pady=2)

        ttk.Label(input_frame, text="Input Baudrate:").grid(row=2, column=0, sticky="w")
        self.input_baud_cb = ttk.Combobox(input_frame, values=[9600, 19200, 38400, 57600, 115200], state="readonly")
        self.input_baud_cb.grid(row=3, column=0, pady=2)
        self.input_baud_cb.set(9600)

        self.connect_input_btn = ttk.Button(input_frame, text="Connect Input", command=self.connect_input_serial)
        self.connect_input_btn.grid(row=4, column=0, pady=4)

        self.disconnect_input_btn = ttk.Button(input_frame, text="Disconnect Input", command=self.disconnect_input_serial, state="disabled")
        self.disconnect_input_btn.grid(row=5, column=0, pady=2)

        self.input_status_label = ttk.Label(input_frame, text="Status: Not Connected", foreground="red")
        self.input_status_label.grid(row=6, column=0, pady=2)

        # === Output ===
        output_frame = ttk.LabelFrame(layout_frame, text="Forwarding Configuration")
        output_frame.grid(row=0, column=1, padx=(255, 40), sticky="n")  # Increased left and right padding

        ttk.Label(output_frame, text="Output COM Port: (e.g., COM9)").grid(row=0, column=0, sticky="w")
        self.output_port_entry = ttk.Entry(output_frame)
        self.output_port_entry.grid(row=1, column=0, pady=2)

        ttk.Label(output_frame, text="Output Baudrate:").grid(row=2, column=0, sticky="w")
        self.output_baud_cb = ttk.Combobox(output_frame, values=[9600, 19200, 38400, 57600, 115200], state="readonly")
        self.output_baud_cb.grid(row=3, column=0, pady=2)
        self.output_baud_cb.set(9600)

        self.connect_output_btn = ttk.Button(output_frame, text="Connect Forwarding", command=self.connect_output_serial)
        self.connect_output_btn.grid(row=4, column=0, pady=4)

        self.disconnect_output_btn = ttk.Button(output_frame, text="Disconnect Forwarding", command=self.disconnect_output_serial, state="disabled")
        self.disconnect_output_btn.grid(row=5, column=0, pady=2)

        self.output_status_label = ttk.Label(output_frame, text="Status: Not Connected", foreground="red")
        self.output_status_label.grid(row=6, column=0, pady=2)

        # === Logs ===
        log_frame = ttk.Frame(root)
        log_frame.pack(pady=10)

        input_log_frame = ttk.LabelFrame(log_frame, text="Input Stdout")
        input_log_frame.grid(row=0, column=0, padx=20)
        self.input_log = scrolledtext.ScrolledText(input_log_frame, width=50, height=15, state="disabled")
        self.input_log.pack()

        output_log_frame = ttk.LabelFrame(log_frame, text="Forwarded Stdout")
        output_log_frame.grid(row=0, column=1, padx=20)
        self.output_log = scrolledtext.ScrolledText(output_log_frame, width=50, height=15, state="disabled")
        self.output_log.pack()

        # === Controls ===
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=5)

        self.start_button = ttk.Button(control_frame, text="Start Proxy", command=self.start_proxy)
        self.start_button.pack(side=tk.LEFT, padx=10)

        self.stop_button = ttk.Button(control_frame, text="Stop Proxy", command=self.stop_proxy, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=10)

    def log_input(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.input_log.config(state='normal')
        self.input_log.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.input_log.yview(tk.END)
        self.input_log.config(state='disabled')

    def log_output(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.output_log.config(state='normal')
        self.output_log.insert(tk.END, f"[{timestamp}] {msg}\n")
        self.output_log.yview(tk.END)
        self.output_log.config(state='disabled')

    def connect_input_serial(self):
        if self.input_ser and self.input_ser.is_open:
            self.log_input("[WARN] Input already connected.")
            return
        try:
            port = self.input_port_entry.get().strip()
            baud = int(self.input_baud_cb.get())
            self.input_ser = serial.Serial(port, baudrate=baud, timeout=1)
            self.input_status_label.config(text=f"Connected to {port}", foreground="green")
            self.connect_input_btn.config(state="disabled")
            self.disconnect_input_btn.config(state="normal")
            self.log_input(f"[INFO] Connected input to {port} @ {baud} baud.")
        except Exception as e:
            self.input_status_label.config(text="Connection Failed", foreground="red")
            self.log_input(f"[ERROR] Input connect failed: {e}")

    def disconnect_input_serial(self):
        try:
            if self.input_ser and self.input_ser.is_open:
                self.input_ser.close()
            self.input_status_label.config(text="Disconnected", foreground="orange")
            self.connect_input_btn.config(state="normal")
            self.disconnect_input_btn.config(state="disabled")
            self.log_input("[INFO] Input disconnected.")
        except Exception as e:
            self.log_input(f"[ERROR] Input disconnect failed: {e}")

    def connect_output_serial(self):
        if self.output_ser and self.output_ser.is_open:
            self.log_output("[WARN] Output already connected.")
            return
        try:
            port = self.output_port_entry.get().strip()
            baud = int(self.output_baud_cb.get())
            self.output_ser = serial.Serial(port, baudrate=baud, timeout=1)
            self.output_status_label.config(text=f"Connected to {port}", foreground="green")
            self.connect_output_btn.config(state="disabled")
            self.disconnect_output_btn.config(state="normal")
            self.log_output(f"[INFO] Connected output to {port} @ {baud} baud.")
        except Exception as e:
            self.output_status_label.config(text="Connection Failed", foreground="red")
            self.log_output(f"[ERROR] Output connect failed: {e}")

    def disconnect_output_serial(self):
        try:
            if self.output_ser and self.output_ser.is_open:
                self.output_ser.close()
            self.output_status_label.config(text="Disconnected", foreground="orange")
            self.connect_output_btn.config(state="normal")
            self.disconnect_output_btn.config(state="disabled")
            self.log_output("[INFO] Output disconnected.")
        except Exception as e:
            self.log_output(f"[ERROR] Output disconnect failed: {e}")

    def start_proxy(self):
        if not (self.input_ser and self.input_ser.is_open):
            self.log_input("[ERROR] Input not connected.")
            return
        if not (self.output_ser and self.output_ser.is_open):
            self.log_output("[ERROR] Output not connected.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        input_path = filedialog.asksaveasfilename(title="Save Input CSV", defaultextension=".csv", initialfile=f"input_{timestamp}.csv")
        forwarded_path = filedialog.asksaveasfilename(title="Save Forwarded CSV", defaultextension=".csv", initialfile=f"forwarded_{timestamp}.csv")

        if not input_path or not forwarded_path:
            self.log_input("[WARN] File selection cancelled.")
            return

        try:
            self.input_csv_file = open(input_path, mode='w', newline='', encoding='utf-8')
            self.input_csv_writer = csv.writer(self.input_csv_file)
            self.input_csv_writer.writerow(["Local Timestamp", "Sensor", "Stress", "Raw Time"])

            self.forwarded_csv_file = open(forwarded_path, mode='w', newline='', encoding='utf-8')
            self.forwarded_csv_writer = csv.writer(self.forwarded_csv_file)
            self.forwarded_csv_writer.writerow(["Local Timestamp", "Sensor", "Stress", "Raw Time"])
        except Exception as e:
            self.log_input(f"[ERROR] Failed to open CSV files: {e}")
            return

        self.running = True
        threading.Thread(target=self.proxy_loop, daemon=True).start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

    def stop_proxy(self):
        self.running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        if self.input_csv_file:
            self.input_csv_file.close()
        if self.forwarded_csv_file:
            self.forwarded_csv_file.close()
        self.log_input("[INFO] Proxy stopped.")
        self.log_output("[INFO] Proxy stopped.")

    def proxy_loop(self):
        while self.running:
            try:
                if self.input_ser.in_waiting:
                    raw_line = self.input_ser.readline().decode(errors='ignore').strip()
                    sensor, stress, time_raw = parse_serial_line(raw_line)
                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    self.log_input(f"Received: {raw_line}")
                    if self.input_csv_writer:
                        self.input_csv_writer.writerow([now, sensor, stress, time_raw])

                    if self.output_ser and self.output_ser.is_open:
                        self.output_ser.write((raw_line + "\n").encode())
                        self.log_output(f"Forwarded: {raw_line}")
                        if self.forwarded_csv_writer:
                            self.forwarded_csv_writer.writerow([now, sensor, stress, time_raw])
            except Exception as e:
                self.log_input(f"[ERROR] Proxy error: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialProxyGUI(root)
    root.mainloop()
