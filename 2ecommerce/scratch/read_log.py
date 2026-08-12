with open("scratch/test_sf_output.log", "r", encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()
    for i, line in enumerate(lines[:20]):
        print(f"{i+1}: {line.strip()}")
