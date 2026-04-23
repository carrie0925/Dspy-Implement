import csv
import json
import re
from pathlib import Path

# ================== 路徑設定（請依需求修改） ==================

# ① CSV → 依模型切成多個 JSON
INPUT_CSV   = Path("UStAI-annotated_V2.csv")  # 這份就是你剛上傳的標註檔
OUTPUT_DIR  = Path("models_json")             # 會在這個資料夾底下輸出每個模型各自的 JSON

# ② [原本功能] TXT → 單一 JSON（沿用你原來的 format_transfer.py）
INPUT_TXT   = Path("g21-badcamp.txt")        # 單行一個 user story 的 txt
OUTPUT_JSON = Path("g21-badcamp.json")       # 轉出來的 JSON 檔名


# ================== 新功能：CSV → 按模型拆成多個 JSON ==================

def sanitize_filename(name: str) -> str:
    """
    把模型名稱（例如 'Gemini_1.5_flash'、'Llama 3.1 70b'）轉成安全的檔名片段。
    會把非英數字元換成底線，並移除前後多餘底線。
    """
    safe = re.sub(r"[^A-Za-z0-9]+", "_", name)
    safe = safe.strip("_")
    return safe or "model"


def csv_to_model_jsons(
    input_path: Path,
    output_dir: Path,
    id_col: str = "ID",
    text_col: str = "User story",
    model_col: str = "LLM",
):
    """
    讀取 UStAI-annotated_V2.csv，依照 model_col（預設 'LLM'）分組，
    為每個模型輸出一個 JSON 檔，格式為
        [
          {"id": <ID欄位>, "description": <User story欄位>},
          ...
        ]
    與 g02-federalspending.json 相同結構。
    """
    if not input_path.exists():
        raise FileNotFoundError(f"Input CSV not found: {input_path}")

    # 讀 CSV，使用 csv.DictReader 可以用欄位名稱取值
    model_buckets: dict[str, list[dict]] = {}

    with input_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            model_name = (row.get(model_col) or "").strip()
            if not model_name:
                # 沒有模型名稱就跳過
                continue

            story_id = (row.get(id_col) or "").strip()
            story_txt = (row.get(text_col) or "").strip()
            if not story_txt:
                # 沒有 user story 內容也可以選擇跳過
                continue

            item = {
                "id": story_id,          # 直接用原本 CSV 的 ID（例如 A1US1Ge）
                "description": story_txt # 對應範本 JSON 的 description
            }
            model_buckets.setdefault(model_name, []).append(item)

    # 建立輸出資料夾
    output_dir.mkdir(parents=True, exist_ok=True)

    # 針對每個模型輸出一個 JSON 檔
    for model_name, items in model_buckets.items():
        safe_name = sanitize_filename(model_name)
        out_path = output_dir / f"{safe_name}.json"

        out_path.write_text(
            json.dumps(items, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        print(f"[OK] {model_name}: {len(items)} stories → {out_path}")


# ================== 保留原本的 TXT → JSON 功能 ==================

def txt_to_json(input_path: Path, output_path: Path):
    """
    保留你原本 format_transfer.py 的功能：
    逐行讀取 txt，每一行變成一個 {"id": "US001", "description": "..."}。
    """
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

    output_path.write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print(f"[OK] Converted {len(items)} items → {output_path}")


# ================== main 區：依需求選擇要跑哪一段 ==================

if __name__ == "__main__":
    # ① 跑 CSV → 依模型拆成多個 JSON
    csv_to_model_jsons(INPUT_CSV, OUTPUT_DIR)

    # ② 如果你還想同時跑原本 TXT → JSON，也可以打開這行：
    # txt_to_json(INPUT_TXT, OUTPUT_JSON)
