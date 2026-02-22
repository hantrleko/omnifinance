import os
import glob
directory = r'e:\Project\Antigravity\Finance\integrated_app\pages'
files = glob.glob(os.path.join(directory, '*.py'))
count = 0
for file in files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    if 'font=dict(color="#FAFAFA")' in content:
        content = content.replace('font=dict(color="#FAFAFA")', 'font=dict()')
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        count += 1
print(f"Updated font colors in {count} files.")
