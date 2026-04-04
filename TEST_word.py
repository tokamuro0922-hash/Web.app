from docx import Document

# ワードファイルのパスを代入
file_path = "/Users/ozeshunsuke/Library/CloudStorage/OneDrive-個人用/グロービス/202404_FANファシリテーション＆ネゴシエーション/Day4/Day4FANレポート_小瀬.docx"

# ワードファイルを読み込む
doc = Document(file_path)

# 本文を格納するリスト
texts = []

# 段落ごとに本文を取得
for para in doc.paragraphs:
    texts.append(para.text)

# 中身を確認
print(texts)