import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog
import serial
import threading
import random
import time
import csv
from datetime import datetime
import os

class SenderGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Raw Serial Sender GUI")
        self.ser = None
        self.running = False
        self.log_filename = ""

        self.sensor_limits = [(tk.StringVar(value="0"), tk.StringVar(value="100")) for _ in range(4)]
        self.sensor_enabled = [tk.BooleanVar(value=True) for _ in range(4)]

        # Serial Configuration Frame with 3 items per row
        serial_frame = ttk.Frame(root)
        serial_frame.pack(pady=5)

        # Row 0
        ttk.Label(serial_frame, text="COM Port: (e.g., COM3):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.port_entry = ttk.Entry(serial_frame)
        self.port_entry.grid(row=1, column=0, padx=5)

        ttk.Label(serial_frame, text="Baudrate:").grid(row=0, column=1, padx=5, pady=2, sticky="w")
        self.baudrate_cb = ttk.Combobox(serial_frame, values=[9600, 19200, 38400, 57600, 115200], state="readonly")
        self.baudrate_cb.grid(row=1, column=1, padx=5)
        self.baudrate_cb.set(9600)

        ttk.Label(serial_frame, text="Parity:").grid(row=0, column=2, padx=5, pady=2, sticky="w")
        self.parity_cb = ttk.Combobox(serial_frame, values=["None", "Even", "Odd", "Mark", "Space"], state="readonly")
        self.parity_cb.grid(row=1, column=2, padx=5)
        self.parity_cb.set("None")

        # Row 1
        ttk.Label(serial_frame, text="Data Bits:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.databits_cb = ttk.Combobox(serial_frame, values=[5, 6, 7, 8], state="readonly")
        self.databits_cb.grid(row=3, column=0, padx=5)
        self.databits_cb.set(8)

        ttk.Label(serial_frame, text="Stop Bits:").grid(row=2, column=1, padx=5, pady=2, sticky="w")
        self.stopbits_cb = ttk.Combobox(serial_frame, values=[1, 1.5, 2], state="readonly")
        self.stopbits_cb.grid(row=3, column=1, padx=5)
        self.stopbits_cb.set(1)

        # Sensor Range Configuration
        ttk.Label(root, text="Sensor Ranges (Min-Max) & Enable:").pack(pady=5)
        for i in range(4):
            frame = ttk.Frame(root)
            frame.pack()
            chk = ttk.Checkbutton(frame, text=f"Sensor {i+1}", variable=self.sensor_enabled[i])
            chk.pack(side=tk.LEFT)
            ttk.Entry(frame, textvariable=self.sensor_limits[i][0], width=5).pack(side=tk.LEFT)
            ttk.Label(frame, text="-").pack(side=tk.LEFT)
            ttk.Entry(frame, textvariable=self.sensor_limits[i][1], width=5).pack(side=tk.LEFT)

        # File Selection
        self.file_btn = ttk.Button(root, text="Choose CSV Save Location", command=self.choose_csv_file)
        self.file_btn.pack(pady=5)

        # Connect / Disconnect Buttons
        button_frame = ttk.Frame(root)
        button_frame.pack(pady=5)

        self.connect_button = ttk.Button(button_frame, text="Connect", command=self.connect_serial)
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_serial, state="disabled")
        self.disconnect_button.pack(side=tk.LEFT, padx=5)

        # Status and Protocol Labels
        self.status_label = ttk.Label(root, text="Status: Not Connected", foreground="red")
        self.status_label.pack()

        self.protocol_label = ttk.Label(root, text="Protocol: Raw Serial", foreground="blue")
        self.protocol_label.pack()

        # Log Output
        self.log = scrolledtext.ScrolledText(root, width=60, height=15, state='disabled')
        self.log.pack(pady=5)

        # Control Buttons in a single horizontal row
        control_frame = ttk.Frame(root)
        control_frame.pack(pady=5)

        self.clear_button = ttk.Button(control_frame, text="Clear Log", command=self.clear_log)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.start_button = ttk.Button(control_frame, text="Start Sending", command=self.start_sending, state="disabled")
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_sending, state="disabled")
        self.stop_button.pack(side=tk.LEFT, padx=5)

    def choose_csv_file(self):
        file_path = filedialog.asksaveasfilename(defaultextension=".csv",
                                                 filetypes=[("CSV files", "*.csv")],
                                                 title="Select CSV file to save")
        if file_path:
            self.log_filename = file_path
            with open(self.log_filename, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Timestamp(ms)", "Human Time", "Sensor", "Stress"])
            self.update_log(f"[INFO] CSV Log File Set: {self.log_filename}")

    def connect_serial(self):
        port_input = self.port_entry.get().strip().upper()
        port = f"COM{port_input}" if port_input.isdigit() else port_input
        baud = int(self.baudrate_cb.get())
        parity = {
            "None": serial.PARITY_NONE,
            "Even": serial.PARITY_EVEN,
            "Odd": serial.PARITY_ODD,
            "Mark": serial.PARITY_MARK,
            "Space": serial.PARITY_SPACE
        }[self.parity_cb.get()]
        databits = int(self.databits_cb.get())
        stopbits = float(self.stopbits_cb.get())

        try:
            if self.ser and self.ser.is_open:
                self.update_log("[WARN] Already connected to a serial port.")
                return

            self.ser = serial.Serial(
                port=port,
                baudrate=baud,
                parity=parity,
                bytesize=databits,
                stopbits=stopbits,
                timeout=1
            )
            self.status_label.config(text=f"Connected to {port}", foreground="green")
            self.protocol_label.config(text="Protocol: Raw Serial")
            self.start_button.config(state="normal")
            self.disconnect_button.config(state="normal")
            self.update_log(f"[INFO] Connected to {port} at {baud} baud.")
        except Exception as e:
            self.status_label.config(text=f"Failed: {e}", foreground="red")
            self.update_log(f"[ERROR] Connection failed: {e}")
            
    def disconnect_serial(self):
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
                self.ser = None
            self.status_label.config(text="Disconnected", foreground="orange")
            self.protocol_label.config(text="Protocol: Not Connected")
            self.start_button.config(state="disabled")
            self.disconnect_button.config(state="disabled")
            self.stop_sending()
        except Exception as e:
            self.status_label.config(text=f"Error disconnecting: {e}", foreground="red")

    def start_sending(self):
        if not self.log_filename:
            self.update_log("[ERROR] Please select a CSV file before starting.")
            return

        self.running = True
        self.thread = threading.Thread(target=self.send_loop, daemon=True)
        self.thread.start()
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")

    def stop_sending(self):
        self.running = False
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")

    def send_loop(self):
        while self.running:
            timestamp = int(time.time() * 1000)
            human_time = datetime.now().strftime("%A, %B %d, %Y %H:%M:%S.%f")[:-3]
            for i in range(4):
                if not self.sensor_enabled[i].get():
                    continue
                try:
                    min_val = int(self.sensor_limits[i][0].get())
                    max_val = int(self.sensor_limits[i][1].get())
                    stress = random.randint(min_val, max_val)
                except ValueError:
                    stress = 0  # fallback

                packet = f"TIME={timestamp};SENSOR={i+1};STRESS={stress}"
                try:
                    if self.ser and self.ser.is_open:
                        self.ser.write((packet + "\n").encode())
                    self.update_log(f"Sent: {packet}")

                    # Write to CSV
                    with open(self.log_filename, 'a', newline='') as csvfile:
                        writer = csv.writer(csvfile)
                        writer.writerow([timestamp, human_time, i + 1, stress])
                except Exception as e:
                    self.update_log(f"Error sending: {e}")
            time.sleep(1)

    def update_log(self, message):
        self.log.config(state='normal')
        self.log.insert(tk.END, message + "\n")
        self.log.yview(tk.END)
        self.log.config(state='disabled')

    def clear_log(self):
        self.log.config(state='normal')
        self.log.delete(1.0, tk.END)
        self.log.config(state='disabled')

if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("600x650")  # 👈 Add this line to make the window square
    app = SenderGUI(root)
    root.mainloop()
