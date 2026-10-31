import os
import glob
import zipfile

# Remove temporary test and debug scripts
eval_dir = os.path.join('code', 'evaluation')
for pat in ['debug_*.py', 'inspect_*.py', 'search_*.py', 'test_*.py']:
    for f in glob.glob(os.path.join(eval_dir, pat)):
        try:
            os.remove(f)
            print("Removed temp script:", f)
        except Exception as e:
            print(f"Error removing {f}: {e}")

# Rebuild code.zip cleanly
zip_path = 'code.zip'
if os.path.exists(zip_path):
    os.remove(zip_path)

with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
    for root, dirs, files in os.walk('code'):
        if '__pycache__' in root:
            continue
        for file in files:
            if file.endswith('.pyc') or file.endswith('.pyo'):
                continue
            fp = os.path.join(root, file)
            arcname = os.path.relpath(fp, 'code')
            z.write(fp, arcname)

print("\nFinal clean code.zip contents:")
with zipfile.ZipFile(zip_path, 'r') as z:
    for info in z.infolist():
        print(f"  {info.filename:35} {info.file_size:>8} bytes")

