import fitz

# PDFファイルのパスを代入
file_path = "/Users/ozeshunsuke/Library/CloudStorage/OneDrive-個人用/グロービス/202404_FANファシリテーション＆ネゴシエーション/Day4/レポート.pdf"

# PDFを読み込む
doc = fitz.open(file_path)

# 各ページの本文を格納するリスト
texts = []

# ページごとに本文を取得
for page in doc:
    text = page.get_text()
    texts.append(text)

# 中身を確認
print(texts)