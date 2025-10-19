import json
from pathlib import Path

# === 路徑設定（如需自訂請改這兩行）===
INPUT_TXT  = Path("g10-scrumalliance.txt")        # 第二個附件（逐行 user story）
OUTPUT_JSON = Path("g10-scrumalliance.json")  # 轉出的 JSON 檔

def txt_to_json(input_path: Path, output_path: Path):
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    items = []
    with input_path.open("r", encoding="utf-8") as f:
        for idx, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line:
                continue  # 跳過空行
            item = {
                "id": f"US{idx:03d}",
                "description": line  # 直接保留原句；如需修飾可在這裡加規則
            }
            items.append(item)

    # 輸出成與示例相同風格的 JSON（縮排、保留非 ASCII）
    output_path.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] Converted {len(items)} items → {output_path}")

if __name__ == "__main__":
    txt_to_json(INPUT_TXT, OUTPUT_JSON)
