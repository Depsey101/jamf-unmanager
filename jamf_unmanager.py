import customtkinter as ctk
import requests
import time
import json
import os
import threading # Added for background tasks
from tkinter import filedialog, messagebox

CONFIG_FILE = os.path.expanduser("~/.jamf_config.json")

class JamfSearchUnmanager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Jamf Pro: Offboard Utility")
        self.geometry("600x550")
        
        self.base_url = ""
        self.token = ""
        self.target_ids = []
        
        self.setup_ui()
        self.load_saved_url()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        
        # --- Login ---
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.grid(row=0, column=0, padx=20, pady=10, sticky="ew")
        self.url_entry = ctk.CTkEntry(self.login_frame, placeholder_text="https://jamf.url.com")
        self.url_entry.pack(side="top", padx=10, pady=(10, 5), fill="x")
        
        self.cred_frame = ctk.CTkFrame(self.login_frame, fg_color="transparent")
        self.cred_frame.pack(side="top", fill="x")
        self.user_entry = ctk.CTkEntry(self.cred_frame, placeholder_text="User")
        self.user_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        self.pass_entry = ctk.CTkEntry(self.cred_frame, placeholder_text="Pass", show="*")
        self.pass_entry.pack(side="left", padx=10, pady=10, expand=True, fill="x")
        
        self.login_btn = ctk.CTkButton(self.login_frame, text="Sign In", command=self.login)
        self.login_btn.pack(side="bottom", padx=10, pady=10, fill="x")

        # --- Search Input ---
        self.search_frame = ctk.CTkFrame(self)
        self.search_frame.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Advanced Search Name")
        self.search_entry.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.fetch_btn = ctk.CTkButton(self.search_frame, text="Load Search", command=self.load_search)
        self.fetch_btn.pack(side="left", padx=10, pady=10)

        self.count_label = ctk.CTkLabel(self, text="Devices found: --", font=("Arial", 14, "bold"))
        self.count_label.grid(row=2, column=0, pady=5)

        # --- Actions ---
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.grid(row=3, column=0, pady=10)
        self.dry_run_btn = ctk.CTkButton(self.btn_frame, text="Dry Run (Export)", state="disabled", command=self.dry_run)
        self.dry_run_btn.pack(side="left", padx=10)
        self.run_btn = ctk.CTkButton(self.btn_frame, text="UNMANAGE ALL", state="disabled", fg_color="#990000", hover_color="#660000", command=self.run_unmanage)
        self.run_btn.pack(side="left", padx=10)

        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=4, column=0, padx=20, pady=10, sticky="ew")
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(self, height=150)
        self.log_box.grid(row=5, column=0, padx=20, pady=10, sticky="nsew")

    def log(self, message):
        # Threads can safely call this to update the UI
        self.log_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.log_box.see("end")

    def load_saved_url(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.url_entry.insert(0, config.get("url", ""))
            except: pass

    def save_url(self, url):
        with open(CONFIG_FILE, 'w') as f:
            json.dump({"url": url}, f)

    def login(self):
            # Capture the URL immediately and ensure it's stored in the class
            self.base_url = self.url_entry.get().strip().rstrip('/')
        
            if not self.base_url or not self.base_url.startswith("http"):
                self.log("❌ Error: Please enter a valid URL (starting with https://)")
                return

            self.save_url(self.base_url)
        
            try:
                res = requests.post(f"{self.base_url}/api/v1/auth/token", auth=(self.user_entry.get(), self.pass_entry.get()))
                if res.status_code == 200:
                    self.token = res.json()['token']
                    self.log("✅ Logged in successfully.")
                else: 
                    self.log(f"❌ Login Error: {res.status_code}")
            except Exception as e: 
                self.log(f"❌ Connection Error: {str(e)}")

    def load_search(self):
            search_name = self.search_entry.get().strip()
            if not search_name: return
            headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        
            try:
                encoded_name = requests.utils.quote(search_name)
                self.target_ids = []
                c_count = 0
                m_count = 0
            
                # 1. Check for Computer Search (macOS)
                url_comp = f"{self.base_url}/JSSResource/advancedcomputersearches/name/{encoded_name}"
                res_c = requests.get(url_comp, headers=headers)
                if res_c.status_code == 200:
                    comps = res_c.json().get('advanced_computer_search', {}).get('computers', [])
                    for c in comps:
                        self.target_ids.append({'id': c['id'], 'name': c.get('name'), 'type': 'computer'})
                        c_count += 1

                # 2. Check for Mobile Device Search (iOS/iPadOS/VisionOS)
                url_mob = f"{self.base_url}/JSSResource/advancedmobiledevicesearches/name/{encoded_name}"
                res_m = requests.get(url_mob, headers=headers)
                if res_m.status_code == 200:
                    mobs = res_m.json().get('advanced_mobile_device_search', {}).get('mobile_devices', [])
                    for m in mobs:
                        self.target_ids.append({'id': m['id'], 'name': m.get('name'), 'type': 'mobile'})
                        m_count += 1

                total = len(self.target_ids)
                # Updated label to show the split
                self.count_label.configure(
                    text=f"Found: {total} ({c_count} Computer / {m_count} Mobile)", 
                    text_color="#2ECC71"
                )
                self.dry_run_btn.configure(state="normal" if total > 0 else "disabled")
                self.run_btn.configure(state="normal" if total > 0 else "disabled")
                self.log(f"✅ Loaded '{search_name}': {c_count} Macs, {m_count} Mobile.")
            
            except Exception as e:
                self.log(f"❌ Error: {str(e)}")

    def dry_run(self):
            path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"DryRun_{int(time.time())}.txt")
            if not path: return
        
            # Split the list for the report
            computers = [i for i in self.target_ids if i['type'] == 'computer']
            mobiles = [i for i in self.target_ids if i['type'] == 'mobile']

            with open(path, "w") as f:
                f.write(f"--- DRY RUN REPORT: {self.search_entry.get()} ---\n")
                f.write(f"Total Devices: {len(self.target_ids)}\n\n")
            
                f.write(f"=== COMPUTERS (macOS) [{len(computers)}] ===\n")
                for item in computers:
                    f.write(f"ID: {item['id']:<8} | Name: {item['name']}\n")
            
                f.write(f"\n=== MOBILE DEVICES (iOS/iPadOS/VisionOS) [{len(mobiles)}] ===\n")
                for item in mobiles:
                    f.write(f"ID: {item['id']:<8} | Name: {item['name']}\n")
                
                f.write(f"\n--- End of Report ---\n")
            
            self.log(f"💾 Organized Dry Run saved to {path}")

    def run_unmanage(self):
        """UI Button Trigger: Starts the background thread."""
        if not messagebox.askyesno("Confirm", f"Proceed with unmanaging {len(self.target_ids)} devices?"):
            return
        
        self.run_btn.configure(state="disabled")
        self.fetch_btn.configure(state="disabled")
        self.login_btn.configure(state="disabled")
        
        # Start the worker thread
        threading.Thread(target=self.unmanage_worker, daemon=True).start()

    def unmanage_worker(self):
            results = []
            total = len(self.target_ids)
        
            for i, item in enumerate(self.target_ids):
                c_id = item['id']
                # Determine endpoint based on device type
                if item['type'] == 'computer':
                    url = f"{self.base_url}/JSSResource/computers/id/{c_id}"
                    payload = "<computer><general><remote_management><managed>false</managed></remote_management></general></computer>"
                else:
                    # Mobile devices (iOS/VisionOS) use a slightly different XML path
                    url = f"{self.base_url}/JSSResource/mobiledevices/id/{c_id}"
                    payload = "<mobile_device><general><managed>false</managed></general></mobile_device>"

                headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/xml"}
            
                try:
                    res = requests.put(url, headers=headers, data=payload)
                    status = "SUCCESS" if res.status_code in [200, 201] else f"FAILED ({res.status_code})"
                    results.append(f"{item['type'].upper()} ID: {c_id} Name: {item.get('name')} -> {status}")
                    self.log(f"[{i+1}/{total}] {item['type'].upper()} {c_id}: {'✅' if 'SUCCESS' in status else '❌'}")
                except Exception as e:
                    results.append(f"ID: {c_id} -> Error: {str(e)}")
            
                self.progress.set((i + 1) / total)
                time.sleep(0.2) 

            self.log("🏁 Batch process complete.")
            self.after(0, lambda: self.finish_process(results))

    def finish_process(self, results):
        self.run_btn.configure(state="normal")
        self.fetch_btn.configure(state="normal")
        self.login_btn.configure(state="normal")
        if messagebox.askyesno("Finished", "Process complete. Save a completion report?"):
            self.save_report(results)

    def save_report(self, results):
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="Offboard_Report.txt")
        if path:
            with open(path, "w") as f:
                f.write("\n".join(results))
            self.log(f"💾 Report saved to {path}")

if __name__ == "__main__":
    app = JamfSearchUnmanager()
    app.mainloop()