from datetime import datetime

def filter_pages(pages, date_range=None, categories=None, authors=None):
    """
    ページ一覧をフィルタする

    Args:
        pages (list): ページ情報のリスト
        date_range (tuple): (start_date, end_date)
        categories (list): カテゴリ一覧
        authors (list): 作成者一覧

    Returns:
        list: フィルタ後のページ
    """

    filtered = []

    # 日付範囲の分解
    if date_range:
        start_date, end_date = date_range
    else:
        start_date = end_date = None

    for page in pages:
        created_at_str = page.get("created_at", "")
        
        # --- 日付変換 ---
        try:
            created_at = datetime.fromisoformat(created_at_str)
        except:
            created_at = None

        # --- 日付フィルタ ---
        if created_at:
            if start_date and created_at.date() < start_date:
                continue
            if end_date and created_at.date() > end_date:
                continue

        # --- カテゴリフィルタ ---
        if categories:
            if page.get("category", "未分類") not in categories:
                continue

        # --- 作成者フィルタ ---
        if authors:
            if page.get("author", "不明") not in authors:
                continue

        filtered.append(page)

    return filtered