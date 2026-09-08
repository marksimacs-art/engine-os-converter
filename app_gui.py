import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from engine_master import EngineOSMasterPipeline, detect_usb_drives

class EngineOSConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Engine OS Converter - Rekordbox Bridge")
        self.geometry("620x540")
        self.resizable(False, False)
        
        # Dark Theme Styling
        self.configure(bg="#1e1e1e")
        self.style = ttk.Style()
        self.style.theme_use("clam")
        
        self.style.configure(".", background="#1e1e1e", foreground="#ffffff", font=("Helvetica", 10))
        self.style.configure("TLabel", background="#1e1e1e", foreground="#ffffff")
        self.style.configure("TFrame", background="#1e1e1e")
        self.style.configure("TButton", background="#333333", foreground="#ffffff", borderwidth=0)
        self.style.map("TButton", background=[("active", "#007acc")])
        self.style.configure("Horizontal.TProgressbar", background="#007acc", troughcolor="#333333")

        self.setup_ui()
        self.refresh_drives()

    def setup_ui(self):
        # Header
        header = ttk.Label(self, text="Rekordbox ➔ Engine OS Converter", font=("Helvetica", 16, "bold"), foreground="#007acc")
        header.pack(pady=15)

        # XML Selection Frame
        xml_frame = ttk.Frame(self)
        xml_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(xml_frame, text="Rekordbox XML Export:").pack(anchor="w")
        self.xml_path_var = tk.StringVar(value="stress_test_5000.xml")
        xml_entry = ttk.Entry(xml_frame, textvariable=self.xml_path_var, width=50)
        xml_entry.pack(side="left", fill="x", expand=True, pady=5)
        
        browse_btn = ttk.Button(xml_frame, text="Browse", command=self.browse_xml)
        browse_btn.pack(side="right", padx=5)

        # Drive Selection Frame
        drive_frame = ttk.Frame(self)
        drive_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(drive_frame, text="Target USB Drive:").pack(anchor="w")
        self.drive_var = tk.StringVar()
        self.drive_dropdown = ttk.Combobox(drive_frame, textvariable=self.drive_var, state="readonly", width=48)
        self.drive_dropdown.pack(side="left", fill="x", expand=True, pady=5)
        
        refresh_btn = ttk.Button(drive_frame, text="Refresh", command=self.refresh_drives)
        refresh_btn.pack(side="right", padx=5)

        # Status & Log Window
        log_frame = ttk.Frame(self)
        log_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        ttk.Label(log_frame, text="Execution Log:").pack(anchor="w")
        self.log_text = tk.Text(log_frame, height=10, bg="#121212", fg="#00ffcc", font=("Courier", 9), insertbackground="white")
        self.log_text.pack(fill="both", expand=True, pady=5)

        # Progress Bar
        self.progress = ttk.Progressbar(self, orient="horizontal", mode="indeterminate", style="Horizontal.TProgressbar")
        self.progress.pack(fill="x", padx=20, pady=5)

        # Convert Button
        self.convert_btn = tk.Button(self, text="START CONVERSION", bg="#007acc", fg="white", font=("Helvetica", 12, "bold"),
                                     activebackground="#005999", activeforeground="white", bd=0, pady=10, command=self.start_conversion_thread)
        self.convert_btn.pack(fill="x", padx=20, pady=15)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def browse_xml(self):
        filename = filedialog.askopenfilename(filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if filename:
            self.xml_path_var.set(filename)

    def refresh_drives(self):
        drives = detect_usb_drives()
        if not drives:
            drives = ["./Test_USB_Drive (Local Folder)"]
        self.drive_dropdown["values"] = drives
        self.drive_dropdown.current(0)

    def start_conversion_thread(self):
        xml_file = self.xml_path_var.get()
        target_drive = self.drive_var.get().split(" ")[0]

        if not os.path.exists(xml_file):
            messagebox.showerror("Error", f"XML file not found: {xml_file}")
            return

        self.convert_btn.config(state="disabled", bg="#555555")
        self.progress.start(10)
        self.log(f"[*] Starting job: {xml_file} ➔ {target_drive}")

        # Run conversion in background thread to keep UI responsive
        threading.Thread(target=self.run_conversion, args=(xml_file, target_drive), daemon=True).start()

    def run_conversion(self, xml_file, target_drive):
        try:
            pipeline = EngineOSMasterPipeline(drive_root_path=target_drive)
            pipeline.initialize_drive_environment()
            self.log("[+] Drive environment ready.")
            
            pipeline.import_rekordbox_xml(xml_file)
            self.log("[+] Successfully parsed tracks, cues, and playlists!")
            pipeline.close()
            self.log("[+] Conversion completed and database unmounted cleanly!")
            messagebox.showinfo("Success", "Conversion Completed Successfully!")
        except Exception as e:
            self.log(f"[!] ERROR: {str(e)}")
            messagebox.showerror("Conversion Failed", str(e))
        finally:
            self.progress.stop()
            self.convert_btn.config(state="normal", bg="#007acc")

if __name__ == "__main__":
    app = EngineOSConverterApp()
    app.mainloop()
