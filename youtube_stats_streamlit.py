import streamlit as st
import pandas as pd
from io import StringIO
from datetime import datetime
from youtube_stats_scraper_ui_final_cleaned_strings import (
    extract_video_id, extract_channel_id, get_video_info_batch
)


def process_csv_video_streamlit(df):
    urls = df["url"].dropna().unique()
    video_ids = []
    url_map = {}
    for url in urls:
        vid = extract_video_id(url)
        if vid:
            video_ids.append(vid)
            url_map[vid] = url
    infos = get_video_info_batch(video_ids)

    output = []
    for info in infos:
        output.append({
            "Ссылка": url_map.get(info["ID видео"], "N/A"),
            "Название канала": info["Название канала"],
            "Название видео": info["Название видео"],
            "Просмотры": info["Просмотры"],
            "Дата сбора": info["Дата сбора"]
        })

    result_df = pd.DataFrame(output)
    out_file = f"video_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    result_df.to_csv(out_file, index=False, encoding='utf-8-sig')
    return out_file, result_df


def analyze_channels_streamlit(df, keywords):
    urls = df["channel_url"].dropna().unique()
    keywords = [kw.strip().lower() for kw in keywords if kw.strip()]
    all_rows = []

    for idx, url in enumerate(urls):
        st.info(f"Анализ канала {idx + 1}/{len(urls)}: {url}")
        channel_id = extract_channel_id(url)
        if not channel_id:
            st.warning(f"Не удалось извлечь ID канала: {url}")
            continue

        uploads_playlist = YOUTUBE.channels().list(part="contentDetails", id=channel_id).execute()
        uploads_id = uploads_playlist["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        video_ids = []
        next_token = None
        while len(video_ids) < 20:
            playlist_response = YOUTUBE.playlistItems().list(
                part="contentDetails",
                playlistId=uploads_id,
                maxResults=50,
                pageToken=next_token
            ).execute()
            for item in playlist_response.get("items", []):
                video_ids.append(item["contentDetails"]["videoId"])
                if len(video_ids) >= 20:
                    break
            next_token = playlist_response.get("nextPageToken")
            if not next_token:
                break

        video_stats = get_video_info_batch(video_ids[:20])
        avg_views = sum(int(v["Просмотры"]) for v in video_stats[:10]) // max(1, len(video_stats[:10]))

        for v in video_stats:
            for kw in keywords:
                if kw in v["Описание"].lower():
                    all_rows.append({
                        "Канал": v["Название канала"],
                        "Ссылка": f"https://youtu.be/{v['ID видео']}",
                        "Название видео": v["Название видео"],
                        "Ключевое слово": kw,
                        "Средние просмотры": avg_views
                    })

    result_df = pd.DataFrame(all_rows)
    out_file = f"channel_keyword_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    result_df.to_csv(out_file, index=False, encoding='utf-8-sig')
    return out_file, result_df


# Streamlit UI
st.set_page_config(page_title="YouTube Stats Scraper", layout="wide")
st.title("📊 YouTube Stats Scraper")

option = st.sidebar.selectbox("Выберите режим:", ["Анализ видео", "Анализ каналов"])

if option == "Анализ видео":
    st.header("🔍 Анализ видео")
    uploaded_file = st.file_uploader("Загрузите CSV с колонкой 'url'", type="csv")

    if uploaded_file:
        df = pd.read_csv(uploaded_file)
        if "url" not in df.columns:
            st.error("❌ CSV должен содержать колонку 'url'")
        else:
            if st.button("Запустить анализ"):
                out_file, result_df = process_csv_video_streamlit(df)
                st.success("✅ Анализ завершён")
                st.download_button("📥 Скачать результат", data=result_df.to_csv(index=False), file_name=out_file, mime="text/csv")
                st.dataframe(result_df)

elif option == "Анализ каналов":
    st.header("🧪 Анализ каналов")
    uploaded_file = st.file_uploader("Загрузите CSV с колонкой 'channel_url'", type="csv")
    keywords_input = st.text_area("Введите ключевые слова (по одному в строке):")
    keywords = keywords_input.strip().splitlines()

    if uploaded_file and keywords:
        df = pd.read_csv(uploaded_file)
        if "channel_url" not in df.columns:
            st.error("❌ CSV должен содержать колонку 'channel_url'")
        else:
            if st.button("Запустить анализ"):
                out_file, result_df = analyze_channels_streamlit(df, keywords)
                st.success("✅ Анализ завершён")
                st.download_button("📥 Скачать результат", data=result_df.to_csv(index=False), file_name=out_file, mime="text/csv")
                st.dataframe(result_df)
