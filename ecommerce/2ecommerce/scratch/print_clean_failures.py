with open("scratch/test_sf_output.log", "r", errors="ignore") as f:
    for i, line in enumerate(f):
        clean_line = line.strip()
        if len(clean_line) > 500:
            clean_line = clean_line[:200] + " ... [TRUNCATED LONG LINE] ... " + clean_line[-200:]
        print(f"{i+1}: {clean_line}")
