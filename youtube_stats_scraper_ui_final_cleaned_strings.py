import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from urllib.parse import urlparse, parse_qs
from datetime import datetime
from googleapiclient.discovery import build

API_KEY = "xxx"
YOUTUBE = build("youtube", "v3", developerKey=API_KEY)

def extract_video_id(url):
    parsed = urlparse(url)
    if 'youtu.be' in parsed.netloc:
        return parsed.path.strip('/')
    if 'youtube.com' in parsed.netloc:
        qs = parse_qs(parsed.query)
        return qs.get('v', [None])[0]
    return None

def extract_channel_id(url):
    if "/channel/" in url:
        return url.split("/channel/")[1].split("/")[0]
    path = urlparse(url).path.strip("/")
    if path.startswith("user/") or path.startswith("c/") or path.startswith("@"):
        identifier = path.split("/")[1] if "/" in path else path
        response = YOUTUBE.search().list(part="snippet", q=identifier, type="channel", maxResults=1).execute()
        items = response.get("items", [])
        if items:
            return items[0]["snippet"]["channelId"]
    return None

def get_video_info_batch(video_ids):
    results = []
    for i in range(0, len(video_ids), 50):
        chunk = video_ids[i:i+50]
        response = YOUTUBE.videos().list(part="snippet,statistics", id=",".join(chunk)).execute()
        for item in response.get("items", []):
            results.append({
                "ID видео": item["id"],
                "Название канала": item["snippet"]["channelTitle"],
                "Название видео": item["snippet"]["title"],
                "Описание": item["snippet"].get("description", ""),
                "Просмотры": item["statistics"].get("viewCount", "0"),
                "Дата сбора": datetime.now().strftime('%Y-%m-%d')
            })
    return results

def process_csv_video(file_path, log_widget):
    try:
        df = pd.read_csv(file_path)
        if "url" not in df.columns:
            messagebox.showerror("Ошибка", "CSV должен содержать колонку 'url'")
            return
        urls = df["url"].dropna().unique()
        video_ids = []
        url_map = {}
        for url in urls:
            vid = extract_video_id(url)
            if vid:
                video_ids.append(vid)
                url_map[vid] = url
        infos = get_video_info_batch(video_ids)

        progressbar["maximum"] = len(infos)
        progressbar["value"] = 0
        for idx, info in enumerate(infos):
            current_url_label.config(text=f"Анализ: {url_map.get(info['ID видео'], '...')}")
            progressbar["value"] = idx + 1
            progressbar.update()
            root.update()

        output = []
        for info in infos:
            output.append({
                "Ссылка": url_map.get(info["ID видео"], "N/A"),
                "Название канала": info["Название канала"],
                "Название видео": info["Название видео"],
                "Просмотры": info["Просмотры"],
                "Дата сбора": info["Дата сбора"]
            })
        out_file = f"video_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        pd.DataFrame(output).to_csv(out_file, index=False, encoding='utf-8-sig')
        log_widget.insert(tk.END, f"✅ Готово! Данные сохранены в {out_file}")
        messagebox.showinfo("Успех", f"Результат сохранён: {out_file}\\n")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

def analyze_channels(file_path, keywords_text, log_widget):
    try:
        df = pd.read_csv(file_path)
        if "channel_url" not in df.columns:
            messagebox.showerror("Ошибка", "CSV должен содержать колонку 'channel_url'")
            return
        urls = df["channel_url"].dropna().unique()
        keywords = [kw.strip().lower() for kw in keywords_text.get("1.0", tk.END).splitlines() if kw.strip()]
        all_rows = []

        progressbar["maximum"] = len(urls)
        progressbar["value"] = 0
        for idx, url in enumerate(urls):
            current_url_label.config(text=f"Анализ канала: {url}")
            progressbar["value"] = idx + 1
            progressbar.update()
            root.update()

            log_widget.insert(tk.END, f"🔍 Обработка: {url}")
            channel_id = extract_channel_id(url)
            if not channel_id:
                log_widget.insert(tk.END, f"⚠️ Пропущен: {url}")
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
            avg_views = sum(int(v["Просмотры"]) for v in video_stats[:10]) // len(video_stats[:10])
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
        out_file = f"channel_keyword_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        pd.DataFrame(all_rows).to_csv(out_file, index=False, encoding='utf-8-sig')
        log_widget.insert(tk.END, f"✅ Готово! Результат сохранён: {out_file}")
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))

def choose_file(entry_widget):
    path = filedialog.askopenfilename(filetypes=[("CSV файлы", "*.csv")])
    entry_widget.delete(0, tk.END)
    entry_widget.insert(0, path)

def main():
    global status_label, current_url_label, progressbar, root

    root = tk.Tk()

    # Статус выполнения
    status_label = tk.Label(root, text="Готов к работе", font=("Arial", 10, "bold"), fg="blue")
    status_label.pack(pady=(5, 0))

    # Текущий обрабатываемый URL
    current_url_label = tk.Label(root, text="", font=("Arial", 9))
    current_url_label.pack()

    # Общий прогресс
    progressbar = ttk.Progressbar(root, length=400, mode='determinate')
    progressbar.pack(pady=(0, 10))
    root.title("YouTube Stats Scraper")

    notebook = ttk.Notebook(root)
    notebook.pack(fill="both", expand=True)

    # Вкладка 1 — анализ видео
    frame1 = tk.Frame(notebook)
    notebook.add(frame1, text="Анализ видео")

    tk.Label(frame1, text="CSV с колонкой 'url':").pack()
    entry1 = tk.Entry(frame1, width=60)
    entry1.pack()
    tk.Button(frame1, text="Выбрать файл", command=lambda: choose_file(entry1)).pack()

    log1 = tk.Text(frame1, height=15, width=90)
    log1.pack()
    tk.Button(frame1, text="Запустить", command=lambda: process_csv_video(entry1.get(), log1)).pack(pady=5)


    # Вкладка 2 — анализ каналов
    frame2 = tk.Frame(notebook)
    notebook.add(frame2, text="Анализ каналов")

    tk.Label(frame2, text="CSV с колонкой 'channel_url':").pack()
    entry2 = tk.Entry(frame2, width=60)
    entry2.pack()
    tk.Button(frame2, text="Выбрать файл", command=lambda: choose_file(entry2)).pack()

    tk.Label(frame2, text="Ключевые слова (по одному в строке):").pack()
    keywords_box = tk.Text(frame2, height=5, width=60)
    keywords_box.pack()

    log2 = tk.Text(frame2, height=15, width=90)
    log2.pack()
    tk.Button(frame2, text="Запустить", command=lambda: analyze_channels(entry2.get(), keywords_box, log2)).pack(pady=5)


    root.mainloop()

if __name__ == "__main__":
    main()
