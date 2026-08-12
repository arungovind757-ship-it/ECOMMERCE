with open("scratch/test_sf_output.log", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "FAIL:" in line or "ERROR:" in line or "Traceback" in line:
        print(f"--- MATCH AT LINE {i+1} ---")
        for j in range(max(0, i-2), min(len(lines), i+15)):
            print(f"{j+1}: {lines[j].strip()}")
