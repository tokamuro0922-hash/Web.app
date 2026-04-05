"""
app.py
フォルダ内ファイル取込に対応した Streamlit アプリ
検索語にヒットした本文箇所を抜き出して表示する改善版
"""

import os
import re
import streamlit as st

from database import init_db, get_all_pages, insert_page, log_search, increment_view_count
from ranking import get_engine, rebuild_index
from crawler import import_folder
from datetime import datetime, timedelta
from filter import filter_pages

today = datetime.today()

if "viewed_pages" not in st.session_state:
    st.session_state.viewed_pages = set()

if "import_results" not in st.session_state:
    st.session_state.import_results = []

init_db()

st.set_page_config(
    page_title="Tech0 Search",
    page_icon="🔍",
    layout="wide"
)


@st.cache_resource
def load_pages():
    """DBから全データを読み込む"""
    return get_all_pages()


def get_file_type_label(file_type: str) -> str:
    """ファイル種別を見やすい表示に変換する"""
    if not file_type:
        return "📄 不明"

    file_type = file_type.lower()
    mapping = {
        "txt": "📝 TXT",
        "md": "📝 Markdown",
        "pdf": "📕 PDF",
        "docx": "📘 Word(.docx)",
        "xlsx": "📗 Excel(.xlsx)",
        "xls": "📗 Excel(.xls)",
        "pptx": "📙 PowerPoint(.pptx)",
    }
    return mapping.get(file_type, f"📄 {file_type}")


def parse_date(date_str):
    try:
        return datetime.fromisoformat(date_str)
    except Exception:
        return datetime.min


def normalize_text_for_preview(text: str) -> str:
    """プレビュー用に改行や余分な空白を整理する"""
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_hit_snippet(full_text: str, query: str, window: int = 60) -> str:
    """
    本文から検索語にヒットした前後文を抜き出す
    ヒットしない場合は先頭を返す
    """
    if not full_text:
        return ""

    text = normalize_text_for_preview(full_text)
    query = (query or "").strip()

    if not query:
        return text[:150] + ("..." if len(text) > 150 else "")

    # 全角スペース対応
    normalized_query = query.replace("　", " ").strip()
    query_parts = [q for q in normalized_query.split() if q]

    # まずは全文に対して順番にヒットを探す
    lower_text = text.lower()

    for q in query_parts:
        idx = lower_text.find(q.lower())
        if idx != -1:
            start = max(0, idx - window)
            end = min(len(text), idx + len(q) + window)
            snippet = text[start:end]

            if start > 0:
                snippet = "..." + snippet
            if end < len(text):
                snippet = snippet + "..."

            return snippet

    # 完全一致しない場合は先頭だけ返す
    return text[:150] + ("..." if len(text) > 150 else "")


def highlight_query(text: str, query: str) -> str:
    """検索語を太字で強調表示する"""
    if not text or not query:
        return text

    highlighted = text
    query_parts = [q for q in query.replace("　", " ").split() if q]

    # 長い語から置換すると崩れにくい
    query_parts = sorted(query_parts, key=len, reverse=True)

    for q in query_parts:
        pattern = re.compile(re.escape(q), re.IGNORECASE)
        highlighted = pattern.sub(lambda m: f"**{m.group(0)}**", highlighted)

    return highlighted


# DBからページ読込
pages = load_pages()

st.title("🔍 Tech0 Search")
st.caption("フォルダ内のファイルを取り込み、全文検索できるアプリ")

# =========================
# サイドバー
# =========================
with st.sidebar:
    st.header("システム情報")
    st.metric("登録ドキュメント数", f"{len(pages)} 件")

    if st.button("🔄 インデックス再読込"):
        st.cache_resource.clear()
        st.rerun()

    st.header("🔎 フィルター")

    date_input_value = st.date_input(
        "更新日フィルター",
        value=(today - timedelta(days=3650), today)
    )

    if isinstance(date_input_value, tuple):
        start_date, end_date = date_input_value
    else:
        start_date = end_date = date_input_value

    date_range = (start_date, end_date)

    sort_option = st.radio(
        "並び順",
        ["関連度順", "更新日（新しい順）", "更新日（古い順）"]
    )

    all_categories = sorted(
        list(set([p.get("category", "未分類") or "未分類" for p in pages]))
    )

    selected_categories = st.multiselect(
        "部署（カテゴリ）",
        options=all_categories,
        default=all_categories
    )

    st.subheader("⭐ その他フィルター")

    min_search_count = st.slider(
        "人気度（検索回数）",
        min_value=0,
        max_value=100,
        value=0
    )

    all_authors = sorted(
        list(set([p.get("author", "不明") or "不明" for p in pages]))
    )

    selected_authors = st.multiselect(
        "作成者",
        options=all_authors,
        default=all_authors
    )

# =========================
# フィルタ済みページ作成
# =========================
filtered_pages = filter_pages(
    pages,
    date_range=date_range,
    categories=selected_categories,
    authors=selected_authors,
)

filtered_pages = [
    p for p in filtered_pages
    if p.get("view_count", 0) >= min_search_count
]

engine = get_engine()
if filtered_pages:
    rebuild_index(filtered_pages)

st.caption(f"全件数: {len(pages)} 件 / フィルタ後: {len(filtered_pages)} 件")

# =========================
# タブ
# =========================
tab_search, tab_import, tab_list = st.tabs(
    ["🔍 検索", "📂 フォルダ取込", "📋 登録一覧"]
)

# =========================
# 検索タブ
# =========================
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

    all_types = sorted(
        list({p.get("file_type", "") for p in filtered_pages if p.get("file_type", "")})
    )

    selected_types = st.multiselect(
        "ファイル種別で絞り込み",
        options=all_types,
        default=[]
    )

    if query:
        if filtered_pages:
            results = engine.search(query, top_n=top_n)
        else:
            results = []

        if selected_types:
            results = [r for r in results if r.get("file_type", "") in selected_types]

        if sort_option == "更新日（新しい順）":
            results = sorted(
                results,
                key=lambda x: parse_date(x.get("crawled_at", "")),
                reverse=True
            )
        elif sort_option == "更新日（古い順）":
            results = sorted(
                results,
                key=lambda x: parse_date(x.get("crawled_at", "")),
                reverse=False
            )

        log_search(query, len(results))

        st.markdown(f"### 検索結果: {len(results)} 件")
        st.divider()

        if results:
            for i, page in enumerate(results, start=1):
                page_id = page.get("id")
                if page_id and page_id not in st.session_state.viewed_pages:
                    increment_view_count(page_id)
                    st.session_state.viewed_pages.add(page_id)

                title = page.get("title", "No Title")
                file_type = page.get("file_type", "")
                file_type_label = get_file_type_label(file_type)
                description = page.get("description", "") or ""
                full_text = page.get("full_text", "") or ""
                file_path = page.get("url", "") or ""
                category = page.get("category", "") or ""
                word_count = page.get("word_count", 0)
                score = page.get("relevance_score", 0)

                snippet = extract_hit_snippet(full_text, query, window=80)
                highlighted_snippet = highlight_query(snippet, query)

                with st.container():
                    col1, col2 = st.columns([5, 1])

                    with col1:
                        st.markdown(f"### {i}. {title}")
                        st.caption(file_type_label)

                    with col2:
                        st.metric("Score", score)
                        st.caption(f"👀 {page.get('view_count', 0)} views")

                    if description:
                        st.write(description)

                    meta1, meta2, meta3, meta4 = st.columns(4)
                    with meta1:
                        st.caption(f"📁 カテゴリ: {category if category else '未設定'}")
                    with meta2:
                        st.caption(f"📊 語数: {word_count}")
                    with meta3:
                        st.caption(f"📂 パス: {file_path}")
                    with meta4:
                        st.caption(f"🕒 更新日: {page.get('crawled_at', '不明')}")

                    if highlighted_snippet:
                        st.markdown("**ヒット箇所**")
                        st.markdown(highlighted_snippet)

                    with st.expander("本文全体を確認"):
                        preview = full_text[:2000]
                        if preview:
                            st.text_area(
                                "本文",
                                value=preview,
                                height=250,
                                disabled=True,
                                key=f"preview_{i}"
                            )
                        else:
                            st.info("本文がありません。")

                    st.divider()
        else:
            st.info("該当する検索結果はありません。")
    else:
        st.info("検索キーワードを入力してください。")

# =========================
# フォルダ取込タブ
# =========================
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

            results = [r for r in results if r is not None]
            st.session_state.import_results = results

            success_count = sum(
                1 for r in results if r.get("crawl_status") == "success"
            )
            fail_count = len(results) - success_count

            st.success(f"スキャン完了: 成功 {success_count} 件 / 失敗 {fail_count} 件")

    if st.session_state.import_results:
        st.markdown("### スキャン結果")

        results = [r for r in st.session_state.import_results if r is not None]

        for i, r in enumerate(results[:100], start=1):
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

        clean_results = [
            r for r in st.session_state.import_results
            if r is not None
        ]

        success_items = [
            r for r in clean_results
            if r.get("crawl_status") == "success"
        ]

        fail_items = [
            r for r in clean_results
            if r.get("crawl_status") != "success"
        ]

        st.success(f"スキャン完了: 成功 {len(success_items)} 件 / 失敗 {len(fail_items)} 件")

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

# =========================
# 登録一覧タブ
# =========================
with tab_list:
    st.subheader(f"登録済みドキュメント一覧（{len(pages)} 件）")

    if not pages:
        st.info("まだドキュメントが登録されていません。")
    else:
        list_types = sorted(
            list({p.get("file_type", "") for p in pages if p.get("file_type", "")})
        )

        selected_list_types = st.multiselect(
            "一覧のファイル種別フィルタ",
            options=list_types,
            default=[],
            key="list_type_filter"
        )

        list_pages = pages
        if selected_list_types:
            list_pages = [p for p in pages if p.get("file_type", "") in selected_list_types]

        st.write(f"表示件数: {len(list_pages)} 件")
        st.divider()

        for i, page in enumerate(list_pages, start=1):
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