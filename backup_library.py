import os
import shutil
from datetime import datetime

def backup_database():
    src = "library.db"
    if not os.path.exists(src):
        print("⚠️ Database does not exist yet.")
        return
    
    # Create backups folder if missing
    os.makedirs("backups", exist_ok=True)

    # Create timestamped filename
    timestamp = datetime.now().strftime("%Y-%m-%d")
    dest = f"backups/library_backup_{timestamp}.db"

    # Copy the file
    shutil.copy2(src, dest)
    print(f"✅ Backup created: {dest}")

if __name__ == "__main__":
    backup_database()