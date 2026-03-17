import customtkinter as ctk
import requests
import time
import json
import os
import threading
from tkinter import filedialog, messagebox

CONFIG_FILE = os.path.expanduser("~/.jamf_config.json")

class JamfSearchUnmanager(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Jamf Pro: Offboard Utility")
        self.geometry("600x650") # Slightly taller to fit new buttons
        
        self.base_url = ""
        self.token = ""
        self.target_ids = []
        
        self.setup_ui()
        self.load_saved_url()

    def setup_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # --- Login ---
        self.login_frame = ctk.CTkFrame(self)
        self.login_frame.grid(row=0, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
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
        self.search_frame.grid(row=1, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.search_entry = ctk.CTkEntry(self.search_frame, placeholder_text="Advanced Search Name")
        self.search_entry.pack(side="left", padx=10, pady=10, fill="x", expand=True)
        self.fetch_btn = ctk.CTkButton(self.search_frame, text="Load Search", command=self.load_search)
        self.fetch_btn.pack(side="left", padx=10, pady=10)

        self.count_label = ctk.CTkLabel(self, text="Devices found: --", font=("Arial", 14, "bold"))
        self.count_label.grid(row=2, column=0, columnspan=2, pady=5)

        # --- Actions ---
        self.dry_run_btn = ctk.CTkButton(self, text="Dry Run (Export)", state="disabled", command=self.dry_run)
        self.dry_run_btn.grid(row=3, column=0, columnspan=2, pady=10)

        # Unmanage Button (Blue)
        self.unmanage_button = ctk.CTkButton(self, text="UNMANAGE ALL", command=self.start_unmanage, state="disabled")
        self.unmanage_button.grid(row=4, column=0, padx=10, pady=10, sticky="ew")

        # Remove MDM Button (Red)
        self.remove_mdm_button = ctk.CTkButton(self, text="REMOVE MDM PROFILE", fg_color="red", hover_color="darkred", command=self.start_removal, state="disabled")
        self.remove_mdm_button.grid(row=4, column=1, padx=10, pady=10, sticky="ew")

        self.progress = ctk.CTkProgressBar(self)
        self.progress.grid(row=5, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(self, height=150)
        self.log_box.grid(row=6, column=0, columnspan=2, padx=20, pady=10, sticky="nsew")

    def log(self, message):
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
        self.base_url = self.url_entry.get().strip().rstrip('/')
        self.user = self.user_entry.get()
        self.pwd = self.pass_entry.get()
        
        if not self.base_url or not self.base_url.startswith("http"):
            self.log("❌ Error: Invalid URL")
            return
        self.save_url(self.base_url)
        try:
            res = requests.post(f"{self.base_url}/api/v1/auth/token", auth=(self.user_entry.get(), self.pass_entry.get()))
            if res.status_code == 200:
                self.token = res.json()['token']
                self.log("✅ Logged in successfully.")
            else: self.log(f"❌ Login Error: {res.status_code}")
        except Exception as e: self.log(f"❌ Connection Error: {str(e)}")

    def load_search(self):
        search_name = self.search_entry.get().strip()
        if not search_name or not self.token: 
            self.log("❌ Error: Not logged in or no search name.")
            return
        headers = {"Authorization": f"Bearer {self.token}", "Accept": "application/json"}
        try:
            encoded_name = requests.utils.quote(search_name)
            self.target_ids = []
            c_count = 0
            m_count = 0
            
            # Check Computers
            res_c = requests.get(f"{self.base_url}/JSSResource/advancedcomputersearches/name/{encoded_name}", headers=headers)
            if res_c.status_code == 200:
                comps = res_c.json().get('advanced_computer_search', {}).get('computers', [])
                for c in comps:
                    self.target_ids.append({'id': c['id'], 'name': c.get('name'), 'type': 'computer'})
                    c_count += 1

            # Check Mobile
            res_m = requests.get(f"{self.base_url}/JSSResource/advancedmobiledevicesearches/name/{encoded_name}", headers=headers)
            if res_m.status_code == 200:
                mobs = res_m.json().get('advanced_mobile_device_search', {}).get('mobile_devices', [])
                for m in mobs:
                    self.target_ids.append({'id': m['id'], 'name': m.get('name'), 'type': 'mobile'})
                    m_count += 1

            total = len(self.target_ids)
            self.count_label.configure(text=f"Found: {total} ({c_count} Computer / {m_count} Mobile)", text_color="#2ECC71")
            self.dry_run_btn.configure(state="normal" if total > 0 else "disabled")
            self.unmanage_button.configure(state="normal" if total > 0 else "disabled")
            self.remove_mdm_button.configure(state="normal" if total > 0 else "disabled")
            self.log(f"✅ Loaded search: {total} devices found.")
        except Exception as e: self.log(f"❌ Error: {str(e)}")

    def dry_run(self):
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile=f"DryRun_{int(time.time())}.txt")
        if not path: return
        with open(path, "w") as f:
            f.write(f"DRY RUN: {len(self.target_ids)} devices found.\n")
            for item in self.target_ids:
                f.write(f"Type: {item['type']} | ID: {item['id']} | Name: {item['name']}\n")
        self.log(f"💾 Dry Run saved to {path}")

    # --- Trigger Functions ---
    def start_unmanage(self):
        if messagebox.askyesno("Confirm", "Unmanage all found devices?"):
            self.toggle_buttons("disabled")
            threading.Thread(target=self.unmanage_worker, daemon=True).start()

    def start_removal(self):
        if messagebox.askyesno("Confirm", "Send Remove MDM Profile command to all found devices?"):
            self.toggle_buttons("disabled")
            threading.Thread(target=self.mdm_removal_worker, daemon=True).start()

    def toggle_buttons(self, state):
        self.unmanage_button.configure(state=state)
        self.remove_mdm_button.configure(state=state)
        self.fetch_btn.configure(state=state)

    # --- Worker Functions ---
    def unmanage_worker(self):
            results = []
            total = len(self.target_ids)
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json"
            }
        
            for i, item in enumerate(self.target_ids):
                device_id = str(item['id'])
            
                # Select endpoint based on type
                if item['type'] == 'computer':
                    url = f"{self.base_url}/api/v1/computers-inventory-detail/{device_id}/unmanage"
                else:
                    url = f"{self.base_url}/api/v2/mobile-devices/{device_id}/unmanage"
            
                try:
                    res = requests.post(url, headers=headers)
                
                    # Jamf returns 204 (No Content) or 200/201 on successful Unmanage
                    success = res.status_code in [200, 201, 202, 204]
                
                    self.log(f"[{i+1}/{total}] Unmanaging {item['type']} {device_id}: {'✅' if success else '❌'}")
                    results.append(f"{item['name']} (ID:{device_id}): {'SUCCESS' if success else 'FAILED'}")
                except Exception as e:
                    self.log(f"Error {device_id}: {e}")
                
                time.sleep(0.3)
                self.progress.set((i + 1) / total)
            
            self.after(0, lambda: self.finish_process(results))

    def mdm_removal_worker(self):
            results = []
            total = len(self.target_ids)
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json"
            }
        
            for i, item in enumerate(self.target_ids):
                try:
                    device_id = str(item['id'])
                    # The modern "Direct Action" endpoint (Jamf Pro 11+)
                    if item['type'] == 'computer':
                        url = f"{self.base_url}/api/v1/computer-inventory/{device_id}/remove-mdm-profile"
                    else:
                        # Mobile devices still often use the v1 mobile-device-inventory path
                        url = f"{self.base_url}/api/v1/mobile-device-inventory/{device_id}/remove-mdm-profile"
                
                    # Note: This is a POST with NO payload
                    res = requests.post(url, headers=headers)
                
                    # Jamf Pro 11 returns 201 (Created) or 202 (Accepted) for these actions
                    success = res.status_code in [200, 201, 202]
                
                    if success:
                        self.log(f"[{i+1}/{total}] Removing MDM {device_id}: ✅ (Action Triggered)")
                    else:
                        # If the specific inventory endpoint fails, it's usually because 
                        # the device is marked 'Unremovable' in the PreStage.
                        print(f"DEBUG: Action failed for {device_id}. Code: {res.status_code} | Resp: {res.text}")
                        self.log(f"❌ ID {device_id} failed. HTTP {res.status_code}")
                
                    results.append(f"{item['name']} (ID:{device_id}): {'SUCCESS' if success else 'FAILED'}")

                except Exception as e: 
                    self.log(f"Error {item['id']}: {e}")
            
                self.progress.set((i + 1) / total)
                time.sleep(0.3) # Avoid API rate-limiting during bulk removal
            
            self.after(0, lambda: self.finish_process(results))

    def finish_process(self, results):
        self.toggle_buttons("normal")
        messagebox.showinfo("Done", "Process complete.")
        if messagebox.askyesno("Save Report", "Would you like to save the results report?"):
            self.save_report(results)

    def save_report(self, results):
        path = filedialog.asksaveasfilename(defaultextension=".txt", initialfile="Action_Report.txt")
        if path:
            with open(path, "w") as f:
                f.write("\n".join(results))
            self.log(f"💾 Report saved to {path}")

if __name__ == "__main__":
    app = JamfSearchUnmanager()
    app.mainloop()