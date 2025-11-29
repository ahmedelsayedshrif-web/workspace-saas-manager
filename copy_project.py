import os
import shutil
from pathlib import Path

# Get desktop path
desktop = Path.home() / "Desktop"
project_dir = desktop / "Workspace_System_Project"

# Source directory (current working directory)
src = Path.cwd()

print(f"جارٍ النسخ من: {src}")
print(f"إلى: {project_dir}")

# Remove existing directory if it exists
if project_dir.exists():
    shutil.rmtree(project_dir)
    print("تم حذف المجلد القديم")

# Create new directory
project_dir.mkdir(parents=True, exist_ok=True)

# Copy all files and directories
for item in src.iterdir():
    if item.name.startswith('.'):
        continue
    dest = project_dir / item.name
    if item.is_dir():
        shutil.copytree(item, dest, dirs_exist_ok=True)
        print(f"تم نسخ المجلد: {item.name}")
    else:
        shutil.copy2(item, dest)
        print(f"تم نسخ الملف: {item.name}")

print(f"\nتم إنشاء النسخة الأساسية بنجاح في: {project_dir}")

