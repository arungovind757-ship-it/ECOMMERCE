import os

extensions = ['.py', '.html']
keywords = ['todo', 'fixme', 'bug', 'issue', 'error', 'broken', 'fail']

root_dir = 'c:/Users/Arch Office/Downloads/ecommerce'

for root, dirs, files in os.walk(root_dir):
    if '.venv' in root or '__pycache__' in root or '.git' in root or '.gemini' in root:
        continue
    for file in files:
        if any(file.endswith(ext) for ext in extensions):
            path = os.path.join(root, file)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for i, line in enumerate(lines):
                    for kw in keywords:
                        if kw in line.lower():
                            print(f"{file}:{i+1} ({kw}): {line.strip()}")
            except Exception as e:
                print(f"Error reading {path}: {e}")
