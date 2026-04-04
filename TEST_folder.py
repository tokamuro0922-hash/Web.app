from pathlib import Path

# フォルダのパスを代入
folder_path = "/Users/ozeshunsuke/Library/CloudStorage/OneDrive-個人用/グロービス/202404_FANファシリテーション＆ネゴシエーション"

# ワードファイルを読み込む
base = Path(folder_path)

allowed_extension = [".txt", ".md", ".pdf", ".docx", ".xlsx", ".pptx"]

allowed_set = {ext.lower() for ext in allowed_extension}

iterator = base.rglob("*")

files = []
for p in iterator:
    if p.is_file() and p.suffix.lower() in allowed_set:
        files.append(p)
        if len(files) >= 200:
            break

print(files)