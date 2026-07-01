import re

filepath = r"c:\Users\17356\.trae-cn\attachments\6a44d2572c92855c061e950b\4ec3e4b3-f6ac-49bf-9105-a09a5d4d0116_exam-2025-a(4).html"

with open(filepath, "rb") as f:
    raw = f.read()

print(f"File size: {len(raw)}")
print(f"First 16 bytes hex: {raw[:16].hex()}")

# Try all encodings
for enc in ["utf-16-le", "utf-16-be", "utf-16", "utf-8-sig", "cp936", "shift_jis", "euc-kr", "big5"]:
    try:
        text = raw.decode(enc)
        if "<html" in text.lower() or "<!doctype" in text.lower() or "<div" in text.lower() or "<head" in text.lower():
            print(f"\n{enc}: SUCCESS, length={len(text)}")
            print(text[:2000])
            print("...")
            print(text[-500:])
            break
    except Exception:
        pass
else:
    # Try to find readable text
    text = raw.decode("latin-1")
    readable = re.findall(r"[a-zA-Z<>/=\-_.\#:;\(\)\{\}\[\],!?@\$]+", text)
    print("Readable chunks:", readable[:20])
    
    # Try to detect if it's XOR or simple cipher
    from collections import Counter
    freq = Counter(raw)
    print("Most common bytes:", freq.most_common(10))