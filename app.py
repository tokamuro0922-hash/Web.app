"""
app.py
フォルダ内ファイル取込に対応した Streamlit アプリ
"""

import os
import streamlit as st

from database import init_db, get_all_pages, insert_page, log_search
from ranking import get_engine, rebuild_index
from crawler import import_folder

init_db()

st.set_page_config(
    page_title="Tech0 Search",
    page_icon="🔍",
    layout="wide"
)


@st.cache_resource
def load_and_index():
    """DBから全データを読み込み、検索インデックスを再構築する"""
    pages = get_all_pages()
    if pages:
        rebuild_index(pages)
    return pages


pages = load_and_index()
engine = get_engine()


def get_file_type_label(file_type: str) -> str:
    """ファイル種別を見やすい表示に変換する"""
    if not file_type:
        return "📄 不明"

    file_type = file_type.lower()
    mapping = {
        "txt": "📝 TXT",
        "md": "📝 Markdown",
        "pdf": "📕 PDF",
        "docx": "📘 Word(.docx)",   #.docファイルはDocumentではうまく取り出せないらしい。今回のデモレベルであれば不要
        "xlsx": "📗 Excel(.xlsx)",
        "xls": "📗 Excel(.xls)",
        "pptx": "📙 PowerPoint(.pptx)",     #.pptファイルもうまく取り出せないらしい。今回のデモレベルであれば不要
    }
    return mapping.get(file_type, f"📄 {file_type}")


st.title("🔍 Tech0 Search")
st.caption("フォルダ内のファイルを取り込み、全文検索できるアプリ")

with st.sidebar:
    st.header("システム情報")
    st.metric("登録ドキュメント数", f"{len(pages)} 件")

    if st.button("🔄 インデックス再構築"):
        st.cache_resource.clear()
        st.rerun()


tab_search, tab_import, tab_list = st.tabs(
    ["🔍 検索", "📂 フォルダ取込", "📋 登録一覧"]
)

with tab_search:
    st.subheader("全文検索")

    col_search, col_topn = st.columns([4, 1])

    with col_search:
        query = st.text_input(
            "検索キーワード",
            placeholder="例: DX / 提案 / 不具合 / 会議 / 売上",
            label_visibility="collapsed"
        )

    with col_topn:
        top_n = st.selectbox("表示件数", [10, 20, 50], index=0)

    all_types = sorted(list({p.get("file_type", "") for p in pages if p.get("file_type", "")}))
    selected_types = st.multiselect(
        "ファイル種別で絞り込み",
        options=all_types,
        default=[]
    )

    if query:
        results = engine.search(query, top_n=top_n)
        log_search(query, len(results))

        if selected_types:
            results = [r for r in results if r.get("file_type", "") in selected_types]

        st.markdown(f"### 検索結果: {len(results)} 件")
        st.divider()

        if results:
            for i, page in enumerate(results, start=1):
                title = page.get("title", "No Title")
                file_type = page.get("file_type", "")
                file_type_label = get_file_type_label(file_type)
                description = page.get("description", "") or ""
                full_text = page.get("full_text", "") or ""
                file_path = page.get("url", "") or ""
                category = page.get("category", "") or ""
                word_count = page.get("word_count", 0)
                score = page.get("relevance_score", 0)

                with st.container():
                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.markdown(f"### {i}. {title}")
                        st.caption(file_type_label)

                    with col2:
                        st.metric("Score", score)

                    if description:
                        st.write(description)

                    meta1, meta2, meta3 = st.columns(3)
                    with meta1:
                        st.caption(f"📁 カテゴリ: {category if category else '未設定'}")
                    with meta2:
                        st.caption(f"📊 語数: {word_count}")
                    with meta3:
                        st.caption(f"📂 パス: {file_path}")

                    preview = full_text[:300]
                    if preview:
                        st.text_area(
                            "本文プレビュー",
                            value=preview,
                            height=120,
                            disabled=True,
                            key=f"preview_{i}"
                        )

                    st.divider()
        else:
            st.info("該当する検索結果はありません。")


if "import_results" not in st.session_state:
    st.session_state.import_results = []

with tab_import:
    st.subheader("フォルダ内ファイルの取込")

    folder_path = st.text_input(
        "フォルダパスを入力",
        placeholder="例: C:\\Users\\xxx\\Documents\\data"
    )

    col1, col2 = st.columns(2)

    with col1:
        recursive = st.checkbox("サブフォルダも含める", value=True)

    with col2:
        max_files = st.number_input(
            "最大取込件数",
            min_value=1,
            max_value=10000,
            value=200,
            step=10
        )

    allowed_exts = st.multiselect(
        "対象拡張子",
        options=[
            ".txt", ".md", ".pdf",
            ".docx", ".xls", ".xlsx", ".pptx"
        ],
        default=[
            ".txt", ".md", ".pdf",
            ".docx", ".xls", ".xlsx", ".pptx"
        ]
    )

    if st.button("📥 フォルダをスキャン"):
        if not folder_path.strip():
            st.error("フォルダパスを入力してください。")
        elif not os.path.exists(folder_path):
            st.error("指定したフォルダが存在しません。")
        elif not os.path.isdir(folder_path):
            st.error("指定したパスはフォルダではありません。")
        elif not allowed_exts:
            st.error("対象拡張子を1つ以上選択してください。")
        else:
            with st.spinner("フォルダ内ファイルをスキャン中..."):
                results = import_folder(
                    folder_path=folder_path,
                    recursive=recursive,
                    allowed_extensions=allowed_exts,
                    max_files=int(max_files)
                )
                st.session_state.import_results = results

            success_count = sum(1 for r in results if r.get("crawl_status") == "success")
            fail_count = len(results) - success_count
            st.success(f"スキャン完了: 成功 {success_count} 件 / 失敗 {fail_count} 件")

    if st.session_state.import_results:
        st.markdown("### スキャン結果")

        for i, r in enumerate(st.session_state.import_results[:100], start=1):
            status = r.get("crawl_status", "unknown")
            icon = "✅" if status == "success" else "❌"

            title = r.get("title", "No Title")
            file_path = r.get("url", "")
            file_type = r.get("file_type", "")
            file_type_label = get_file_type_label(file_type)

            with st.expander(f"{icon} {i}. {title}"):
                st.write(f"**ファイル種別:** {file_type_label}")
                st.write(f"**パス:** {file_path}")
                st.write(f"**語数:** {r.get('word_count', 0)}")

                if r.get("error_message"):
                    st.error(r["error_message"])

        success_items = [
            r for r in st.session_state.import_results
            if r.get("crawl_status") == "success"
        ]

        if success_items:
            st.info(f"{len(success_items)} 件のファイルをDB登録できます。")

            if st.button("💾 成功したファイルをDBに登録"):
                total = len(success_items)
                progress_bar = st.progress(0)
                progress_text = st.empty()

                for i, item in enumerate(success_items, start=1):
                    insert_page(item)
                    progress_bar.progress(i / total)
                    progress_text.write(f"登録中... {i}/{total}")

                st.success(f"{total} 件のファイルを登録しました。")
                st.session_state.import_results = []
                st.cache_resource.clear()
                st.rerun()


with tab_list:
    st.subheader(f"登録済みドキュメント一覧（{len(pages)} 件）")

    if not pages:
        st.info("まだドキュメントが登録されていません。")
    else:
        list_types = sorted(list({p.get("file_type", "") for p in pages if p.get("file_type", "")}))
        selected_list_types = st.multiselect(
            "一覧のファイル種別フィルタ",
            options=list_types,
            default=[],
            key="list_type_filter"
        )

        filtered_pages = pages
        if selected_list_types:
            filtered_pages = [p for p in pages if p.get("file_type", "") in selected_list_types]

        st.write(f"表示件数: {len(filtered_pages)} 件")
        st.divider()

        for i, page in enumerate(filtered_pages, start=1):
            title = page.get("title", "No Title")
            file_type = page.get("file_type", "")
            file_type_label = get_file_type_label(file_type)
            file_path = page.get("url", "") or ""
            category = page.get("category", "") or ""
            word_count = page.get("word_count", 0)
            description = page.get("description", "") or ""
            full_text = page.get("full_text", "") or ""

            with st.expander(f"{i}. {title}"):
                st.write(f"**ファイル種別:** {file_type_label}")
                st.write(f"**パス:** {file_path}")
                st.write(f"**カテゴリ:** {category if category else '未設定'}")
                st.write(f"**語数:** {word_count}")

                if description:
                    st.write(f"**説明:** {description}")

                preview = full_text[:500]
                if preview:
                    st.text_area(
                        "本文プレビュー",
                        value=preview,
                        height=180,
                        disabled=True,
                        key=f"list_preview_{i}"
                    )

st.divider()
st.caption("© Tech0 Search | Folder Import + Full Text Search")