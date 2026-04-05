import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ocr_pdf(file_path):
    """写真データのPDFをOCR化してフルテキストとして出力"""

    # 1. PDFをOpenAIにアップロード
    with open(file_path, "rb") as f:
        uploaded = client.files.create(
            file=f,
            purpose="user_data"
        )

    print("uploaded file_id:", uploaded.id)

    # 2. そのfile_idをResponses APIに渡す
    response = client.responses.create(
        model="gpt-5-nano",
        input=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_file",
                        "file_id": uploaded.id,
                    },
                    {
                        "type": "input_text",
                        "text": """
                        このPDFをフルテキスト化してください。

                        ルール：
                        ・ページ順に全文を出力
                        ・改行、段落をできるだけ忠実に再現
                        ・省略禁止
                        ・推測で補完しない
                        ・読めない箇所は [判読不可] と記載
                        ・フルテキスト化できない場合は「''」のみ出力
                        """
                    }
                ]
            }
        ]
    )

    return response.output_text