import os
import json
import struct
import html
import hashlib
import time
import urllib.parse
try:
    import requests
except ImportError:
    print("Ошибка: Для работы с API Civitai нужна библиотека requests.")
    print("Установите её командой: pip install requests")
    exit(1)

DB_FILE = "lora_database.json"
# Оставляем ту же версию, чтобы использовать уже собранные данные и медиа из кеша
CACHE_VERSION = "1.3_local_media"

def calculate_sha256(file_path):
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4 * 1024 * 1024), b""):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()

def get_civitai_info(hash_value, retries=3):
    api_url = f"https://civitai.com/api/v1/model-versions/by-hash/{hash_value}"
    for attempt in range(retries):
        try:
            response = requests.get(api_url, timeout=30)
            if response.status_code == 200: return response.json()
            elif response.status_code == 404: return {}
            elif response.status_code == 429:
                wait_time = 5 * (attempt + 1)
                print(f"  [!] Лимит запросов Civitai. Ждем {wait_time} сек...")
                time.sleep(wait_time)
            else: time.sleep(2)
        except requests.exceptions.Timeout: time.sleep(3)
        except Exception: time.sleep(2)
    return {}

def parse_safetensors_header(filepath):
    try:
        with open(filepath, 'rb') as f:
            header_size_bytes = f.read(8)
            if len(header_size_bytes) < 8: return {}
            header_size = struct.unpack('<Q', header_size_bytes)[0]
            if header_size > 100 * 1024 * 1024: return {}
            header_bytes = f.read(header_size)
            header = json.loads(header_bytes.decode('utf-8'))
            return header.get('__metadata__', {})
    except: return {}

def generate_html(data, total_gb, output_path):
    # Собираем уникальные базовые модели для вкладок
    base_models = set()
    for item in data:
        b = item["Base Model"] if item["Base Model"] else "Unknown Base"
        base_models.add(b)
    base_models = sorted(list(base_models))

    # Формируем HTML кнопок
    tabs_html = '<div class="tabs">\n'
    tabs_html += '<button class="tab-btn active" data-base="All" onclick="filterByBaseModel(this)">ALL</button>\n'
    for b in base_models:
        safe_b = html.escape(b)
        tabs_html += f'<button class="tab-btn" data-base="{safe_b}" onclick="filterByBaseModel(this)">{safe_b}</button>\n'
    tabs_html += '</div>\n'

    html_content = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LORA Collection</title>
    <style>
        :root {{
            --bg-color: #121212; --card-bg: #1e1e24; --text-main: #e0e0e0;
            --text-muted: #9e9e9e; --accent: #bb86fc; --border: #333; --code-bg: #2a2a35;
        }}
        * {{ box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', system-ui, sans-serif; background-color: var(--bg-color); color: var(--text-main); margin: 0; padding: 20px; }}
        
        .container {{ width: 100%; margin: 0 auto; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 15px; }}
        .header-stats {{ display: flex; gap: 15px; align-items: center; flex-wrap: wrap; }}
        .stat-badge {{ background: #2a2a35; padding: 8px 15px; border-radius: 8px; font-weight: bold; border: 1px solid #444; }}
        #searchInput {{ padding: 10px 15px; border-radius: 8px; border: 1px solid var(--border); background: var(--card-bg); color: var(--text-main); width: 100%; max-width: 400px; font-size: 16px; }}
        
        /* Стили для вкладок */
        .tabs {{ display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 25px; }}
        .tab-btn {{ background: var(--card-bg); color: var(--text-muted); border: 1px solid var(--border); padding: 8px 16px; border-radius: 20px; cursor: pointer; transition: all 0.2s; font-weight: bold; font-size: 0.9rem; }}
        .tab-btn:hover {{ background: #2a2a35; color: var(--text-main); border-color: #555; }}
        .tab-btn.active {{ background: rgba(187, 134, 252, 0.15); color: var(--accent); border-color: rgba(187, 134, 252, 0.5); }}

        .grid {{ display: flex; flex-direction: column; gap: 20px; }}
        
        .card {{ background: var(--card-bg); border: 1px solid var(--border); border-radius: 12px; padding: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.2); transition: transform 0.2s; width: 100%; }}
        .card h3 {{ margin: 0 0 10px 0; font-size: 1.4rem; word-break: break-all; }}
        
        .badges {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 15px; }}
        .badge {{ background: rgba(187, 134, 252, 0.2); color: var(--accent); padding: 4px 8px; border-radius: 6px; font-size: 0.85rem; font-weight: bold; border: 1px solid rgba(187, 134, 252, 0.3); }}
        .badge-hash {{ background: var(--code-bg); color: #aaa; font-family: monospace; border-color: #444; cursor: pointer; }}
        .badge-size {{ background: rgba(76, 175, 80, 0.2); color: #4CAF50; border-color: rgba(76, 175, 80, 0.3); }}
        
        .section-title {{ font-size: 0.9rem; color: var(--text-muted); text-transform: uppercase; margin: 15px 0 10px 0; letter-spacing: 0.5px; }}
        .triggers {{ background: var(--code-bg); padding: 12px; border-radius: 6px; font-family: monospace; font-size: 1rem; color: #fff; word-break: break-word; cursor: pointer; position: relative; }}
        .triggers:hover::after, .badge-hash:hover::after {{ content: "Кликни для копирования"; position: absolute; right: 12px; top: 12px; font-size: 0.75rem; color: var(--accent); font-family: sans-serif; }}
        
        .image-gallery {{ display: flex; overflow-x: auto; gap: 15px; padding-bottom: 10px; }}
        .image-gallery::-webkit-scrollbar {{ height: 8px; }}
        .image-gallery::-webkit-scrollbar-thumb {{ background: #555; border-radius: 4px; }}
        .image-item {{ flex: 0 0 300px; background: #18181c; border: 1px solid var(--border); border-radius: 8px; overflow: hidden; display: flex; flex-direction: column; }}
        
        .media-container {{ width: 100%; height: 300px; position: relative; cursor: pointer; background: #000; }}
        .media-container img, .media-container video {{ width: 100%; height: 100%; object-fit: cover; }}
        .play-icon {{ position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); background: rgba(0,0,0,0.6); color: white; border-radius: 50%; width: 50px; height: 50px; display: flex; justify-content: center; align-items: center; font-size: 24px; pointer-events: none; border: 2px solid rgba(255,255,255,0.8); }}
        
        .image-prompt {{ padding: 10px; font-size: 0.85rem; color: #bbb; max-height: 120px; overflow-y: auto; font-family: monospace; cursor: pointer; transition: background 0.2s; word-break: break-word; flex-grow: 1; }}
        .image-prompt::-webkit-scrollbar {{ width: 4px; }}
        .image-prompt::-webkit-scrollbar-thumb {{ background: #444; border-radius: 2px; }}
        .image-prompt:hover {{ background: #2a2a35; color: #fff; }}
        
        .meta-details {{ margin-top: 15px; font-size: 0.9rem; }}
        .meta-details summary {{ cursor: pointer; color: var(--accent); user-select: none; padding: 5px 0; }}
        .meta-list {{ list-style: none; padding: 15px; margin: 10px 0 0 0; background: #18181c; border-radius: 6px; max-height: 200px; overflow-y: auto; }}
        .meta-list li {{ margin-bottom: 8px; border-bottom: 1px solid #333; padding-bottom: 8px; word-break: break-word; }}
        .meta-list li:last-child {{ border-bottom: none; margin: 0; padding: 0; }}
        .meta-key {{ color: var(--text-muted); }}
        .bottom-info {{ display: flex; justify-content: space-between; align-items: flex-end; margin-top: 15px; }}
        .link {{ color: var(--accent); text-decoration: none; font-size: 0.95rem; font-weight: bold; }}
        .link:hover {{ text-decoration: underline; }}
        .file-path {{ font-size: 0.8rem; color: #666; word-break: break-all; text-align: right; }}

        #mediaModal {{ display: none; position: fixed; z-index: 1000; left: 0; top: 0; width: 100%; height: 100%; background-color: rgba(0,0,0,0.9); backdrop-filter: blur(5px); justify-content: center; align-items: center; flex-direction: column; }}
        .modal-content {{ max-width: 95%; max-height: 85%; display: flex; justify-content: center; align-items: center; position: relative; }}
        .modal-content img, .modal-content video {{ max-width: 100%; max-height: 80vh; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); object-fit: contain; }}
        .close-modal {{ position: absolute; top: 20px; right: 30px; color: #aaa; font-size: 40px; font-weight: bold; cursor: pointer; z-index: 1001; transition: color 0.2s; }}
        .close-modal:hover {{ color: #fff; }}
        .modal-prompt {{ margin-top: 20px; color: #fff; background: var(--card-bg); padding: 15px; border-radius: 8px; width: 95%; max-width: 800px; text-align: left; word-wrap: break-word; overflow-y: auto; max-height: 15vh; font-family: monospace; border: 1px solid var(--border); cursor: pointer; }}
        .modal-prompt:hover {{ border-color: var(--accent); }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-stats">
                <h1>LORA Collection</h1>
                <span class="stat-badge">Найдено: {len(data)} шт.</span>
                <span class="stat-badge">Общий вес: {total_gb:.2f} ГБ</span>
            </div>
            <input type="text" id="searchInput" placeholder="Поиск по названию, тегам или базе..." onkeyup="applyFilters()">
        </div>
        
        {tabs_html}

        <div class="grid" id="cardGrid">
"""

    for item in data:
        name = html.escape(item["File Name"])
        base = html.escape(item["Base Model"]) if item["Base Model"] else "Unknown Base"
        triggers = html.escape(item["Trigger Words"]) if item["Trigger Words"] else "Нет триггеров"
        path = html.escape(item["File Path"])
        url = item["URL"]
        size = html.escape(item.get("Size", "N/A"))
        sha256 = html.escape(item.get("SHA256", "N/A"))
        images = item.get("Images", [])
        
        # Добавили data-base-model для фильтрации
        card_html = f'''
        <div class="card" data-search="{name.lower()} {base.lower()} {triggers.lower()}" data-base-model="{base}">
            <h3>{name}</h3>
            <div class="badges">
                <span class="badge">{base}</span>
                <span class="badge badge-size">{size}</span>
                <span class="badge badge-hash" onclick="navigator.clipboard.writeText('{sha256}')" title="SHA256 Hash">SHA256: {sha256[:10]}...</span>
            </div>
            <div class="section-title">Trigger Words</div>
            <div class="triggers" onclick="navigator.clipboard.writeText(this.innerText)">{triggers}</div>
        '''
        
        if images:
            card_html += '<div class="section-title">Examples & Prompts</div><div class="image-gallery">'
            for img in images:
                img_url = html.escape(img["url"])
                img_prompt_escaped = html.escape(img["prompt"]) if img["prompt"] else "Промпт скрыт автором"
                is_video = img.get("is_video", False)
                media_type = "video" if is_video else "image"
                
                if is_video:
                    media_html = f'''
                    <video src="{img_url}#t=0.1" preload="metadata" muted playsinline></video>
                    <div class="play-icon">▶</div>
                    '''
                else:
                    media_html = f'<img src="{img_url}" loading="lazy" alt="Example">'

                card_html += f'''
                <div class="image-item">
                    <div class="media-container" data-url="{img_url}" data-type="{media_type}" data-prompt="{img_prompt_escaped}" onclick="openModal(this)">
                        {media_html}
                    </div>
                    <div class="image-prompt" title="Кликни для копирования" onclick="navigator.clipboard.writeText(this.innerText)">
                        <strong>Prompt:</strong><br>{img_prompt_escaped}
                    </div>
                </div>
                '''
            card_html += '</div>'
            
        if item["Extra Meta"]:
            card_html += '<div class="meta-details"><details><summary>Training Meta & Details</summary><ul class="meta-list">'
            for k, v in item["Extra Meta"].items():
                card_html += f'<li><span class="meta-key">{html.escape(k)}:</span> {html.escape(str(v)[:500])}</li>'
            card_html += '</ul></details></div>'
            
        card_html += '<div class="bottom-info">'
        if url:
            card_html += f'<a href="{url}" target="_blank" class="link">🔗 Открыть на Civitai</a>'
        else:
            card_html += '<span></span>'
        card_html += f'<div class="file-path">{path}</div></div></div>'
        html_content += card_html

    html_content += """
        </div>
    </div>

    <div id="mediaModal" onclick="closeModal()">
        <span class="close-modal" onclick="closeModal()">&times;</span>
        <div class="modal-content" onclick="event.stopPropagation()">
            <div id="modalMediaContainer"></div>
        </div>
        <div id="modalPrompt" class="modal-prompt" title="Кликни для копирования" onclick="copyModalPrompt(event)"></div>
    </div>

    <script>
        let currentBaseModelFilter = 'All';

        function filterByBaseModel(btnElement) {
            // Получаем выбранную базу
            currentBaseModelFilter = btnElement.getAttribute('data-base');
            
            // Обновляем активную кнопку
            const tabs = document.getElementsByClassName('tab-btn');
            for (let i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove('active');
            }
            btnElement.classList.add('active');
            
            // Применяем фильтры
            applyFilters();
        }

        function applyFilters() {
            const searchInput = document.getElementById('searchInput').value.toLowerCase();
            const cards = document.getElementsByClassName('card');
            
            for (let i = 0; i < cards.length; i++) {
                const searchData = cards[i].getAttribute('data-search');
                const cardBaseModel = cards[i].getAttribute('data-base-model');
                
                const matchesSearch = searchData.includes(searchInput);
                const matchesBase = (currentBaseModelFilter === 'All' || cardBaseModel === currentBaseModelFilter);
                
                cards[i].style.display = (matchesSearch && matchesBase) ? "flex" : "none";
            }
        }

        let currentPromptText = "";

        function openModal(element) {
            const url = element.getAttribute('data-url');
            const type = element.getAttribute('data-type');
            const prompt = element.getAttribute('data-prompt');
            
            const modal = document.getElementById('mediaModal');
            const container = document.getElementById('modalMediaContainer');
            const promptContainer = document.getElementById('modalPrompt');
            
            container.innerHTML = '';
            currentPromptText = prompt;
            
            if (type === 'video') {
                container.innerHTML = `<video src="${url}" controls autoplay loop></video>`;
            } else {
                container.innerHTML = `<img src="${url}">`;
            }
            
            if (prompt) {
                promptContainer.innerHTML = `<strong>Prompt:</strong><br>${prompt}`;
                promptContainer.style.display = 'block';
            } else {
                promptContainer.style.display = 'none';
            }
            
            modal.style.display = 'flex';
        }

        function closeModal() {
            const modal = document.getElementById('mediaModal');
            const container = document.getElementById('modalMediaContainer');
            modal.style.display = 'none';
            container.innerHTML = ''; 
        }

        function copyModalPrompt(event) {
            event.stopPropagation();
            if (currentPromptText) {
                navigator.clipboard.writeText(currentPromptText);
                const btn = document.getElementById('modalPrompt');
                const origBg = btn.style.background;
                btn.style.background = '#4CAF50';
                setTimeout(() => { btn.style.background = origBg; }, 300);
            }
        }

        document.addEventListener('keydown', function(event) {
            if (event.key === "Escape") closeModal();
        });
    </script>
</body>
</html>
"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

def extract_lora_info(directory, output_path):
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            db_cache = json.load(f)
    else:
        db_cache = {}
        
    lora_data = []
    total_size_bytes = 0
    temp_base_dir = os.path.join(directory, "_temp")

    try:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith((".safetensors", ".pt", ".ckpt")):
                    filepath = os.path.join(root, file)
                    
                    file_stat = os.stat(filepath)
                    file_size_bytes = file_stat.st_size
                    total_size_bytes += file_size_bytes
                    
                    file_size_mb = file_size_bytes / (1024 * 1024)
                    file_size_str = f"{file_size_mb:.2f} MB"
                    cache_key = f"{file}_{file_size_bytes}"
                    
                    if cache_key in db_cache and db_cache[cache_key].get('cache_version') == CACHE_VERSION:
                        print(f"⏭ Пропуск: {file} (Взято из кеша)")
                        item = db_cache[cache_key]['data']
                        item['File Path'] = filepath 
                        lora_data.append(item)
                        continue
                        
                    print(f"🔄 Обработка: {file}")
                    
                    file_hash = calculate_sha256(filepath)
                    civitai_info = get_civitai_info(file_hash)
                    time.sleep(0.5)
                    
                    st_meta = parse_safetensors_header(filepath) if file.endswith(".safetensors") else {}
                    
                    triggers = set()
                    if civitai_info.get("trainedWords"):
                        for word in civitai_info["trainedWords"]: triggers.add(word.strip())
                            
                    if not triggers and 'ss_tag_frequency' in st_meta:
                        try:
                            tag_freq = json.loads(st_meta['ss_tag_frequency'])
                            for _, tags in tag_freq.items():
                                for tag in tags.keys(): triggers.add(tag.strip())
                        except: pass
                    
                    base_model = civitai_info.get("baseModel", "")
                    if not base_model and 'ss_base_model_version' in st_meta:
                        base_model = st_meta['ss_base_model_version']

                    images_data = []
                    if civitai_info.get("images"):
                        base_name = os.path.splitext(file)[0]
                        lora_temp_dir = os.path.join(temp_base_dir, base_name)
                        os.makedirs(lora_temp_dir, exist_ok=True)
                        
                        for i, img in enumerate(civitai_info["images"]):
                            remote_url = img.get("url")
                            img_prompt = ""
                            if img.get("meta") and "prompt" in img["meta"]:
                                img_prompt = img["meta"]["prompt"].replace('\n', ' ')
                            
                            is_video = img.get("type") == "video" or (remote_url and remote_url.lower().endswith(('.mp4', '.webm')))
                            
                            if remote_url:
                                ext = ".mp4" if is_video else ".jpeg"
                                if "." in remote_url.split("/")[-1]:
                                    possible_ext = "." + remote_url.split("/")[-1].split(".")[-1].split("?")[0]
                                    if len(possible_ext) <= 5: 
                                        ext = possible_ext
                                
                                local_filename = f"{i}{ext}"
                                local_filepath = os.path.join(lora_temp_dir, local_filename)
                                safe_base_name = urllib.parse.quote(base_name)
                                rel_html_url = f"_temp/{safe_base_name}/{local_filename}"
                                
                                if not os.path.exists(local_filepath):
                                    print(f"    ⬇️ Скачивание превью {i+1}...")
                                    for attempt in range(2):
                                        try:
                                            media_resp = requests.get(remote_url, stream=True, timeout=15)
                                            if media_resp.status_code == 200:
                                                with open(local_filepath, 'wb') as mf:
                                                    for chunk in media_resp.iter_content(1024 * 1024):
                                                        mf.write(chunk)
                                                break
                                            elif media_resp.status_code == 404:
                                                break
                                        except Exception as e:
                                            time.sleep(1)
                                
                                final_url = rel_html_url if os.path.exists(local_filepath) else remote_url
                                images_data.append({"url": final_url, "prompt": img_prompt, "is_video": is_video})
                    
                    url = f"https://civitai.com/models/{civitai_info['modelId']}" if civitai_info.get("modelId") else ""

                    data_row = {
                        "File Name": file,
                        "File Path": filepath,
                        "Size": file_size_str,
                        "SHA256": file_hash,
                        "Trigger Words": ", ".join(triggers),
                        "Base Model": base_model,
                        "URL": url,
                        "Images": images_data,
                        "Extra Meta": {k: str(v) for k, v in st_meta.items() if k not in ['ss_tag_frequency']}
                    }
                    
                    lora_data.append(data_row)
                    
                    db_cache[cache_key] = {
                        'cache_version': CACHE_VERSION,
                        'data': data_row
                    }
                    with open(DB_FILE, 'w', encoding='utf-8') as f:
                        json.dump(db_cache, f, ensure_ascii=False, indent=4)
                    
                    current_gb = total_size_bytes / (1024 ** 3)
                    generate_html(lora_data, current_gb, output_path)

    except KeyboardInterrupt:
        print("\n[!] Остановка скрипта пользователем (Ctrl+C).")
        print("Формирование финального HTML файла из обработанных данных...")

    total_gb = total_size_bytes / (1024 ** 3)
    return lora_data, total_gb

def main():
    directory = os.getcwd()
    output_path = os.path.join(directory, "lora_index.html")
    print(f"Сканирование папки: {directory}")
    print("Вы можете в любой момент нажать Ctrl+C для безопасной остановки.")
    
    data, total_gb = extract_lora_info(directory, output_path)
    
    if not data:
        print("Файлы LORA (.safetensors, .pt, .ckpt) не найдены.")
        return
        
    generate_html(data, total_gb, output_path)
    
    print(f"\nГотово! Успешно обработано файлов: {len(data)}")
    print(f"Общий вес файлов: {total_gb:.2f} ГБ")
    print(f"Результат сохранен в: {output_path}")

if __name__ == "__main__":
    main()
