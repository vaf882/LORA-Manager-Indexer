# LORA-Manager-Indexer
LORA Manager - это легковесный, быстрый и автономный Python-скрипт для парсинга, управления и визуализации вашей коллекции LORA моделей для ComfyUI

Скрипт писался для того, чтобы решить главную боль при работе с сотнями LORA — вспомнить, что именно делает модель, какое у нее триггерное слово и как выглядит результат, без необходимости каждый раз лезть на Civitai.

Скрипт сканирует папку с моделями, быстро извлекает метаданные и генерирует автономную, визуально приятную HTML-галерею с фильтрами, поиском и медиа-плеером прямо в вашем браузере. Забудьте про ручной поиск триггерных слов на Civitai!

✨Ключевые возможности
- Умный кеш (lora_database.json): Скрипт мгновенно пропускает уже обработанные модели, сверяя их точный размер. Повторные сканирования даже терабайтной коллекции занимают секунды.
- Автономные превью: Картинки и видео с Civitai автоматически скачиваются в папку _temp/. Ваша галерея будет загружаться мгновенно и работать без интернета.
- Встроенный медиаплеер (Popup Lightbox): Поддержка .mp4 и .webm видео-превью. Кликните на любое изображение или видео, чтобы открыть его на весь экран вместе с промптом генерации.
- Динамические вкладки: Автоматическая фильтрация LORA по базовой модели (например, переключение между SD 1.5, SDXL и Flux в один клик).
- Click-to-Copy: Копируйте длинные промпты и триггерные слова в буфер обмена простым кликом.
- Прямое чтение заголовков: Скрипт читает метаданные (Kohya SS, ModelSpec) напрямую из бинарного заголовка .safetensors, не загружая тяжелые веса модели в оперативную память.
- Защита от сбоев: Можете прервать работу Ctrl+C в любой момент — скрипт сохранит прогресс и сгенерирует галерею для уже обработанных моделей.

📦 Установка и запуск
- Скачайте lora_indexer.py в папку с вашими моделями (например, ComfyUI/models/loras).
- Установите зависимость requests (если не установлена):

pip install requests

Запустите скрипт:

python lora_indexer.py
Откройте сгенерированный lora_index.html в любом браузере.

LORA Manager is a lightweight, fast, and standalone Python script for parsing, managing, and visualizing your collection of LORA models for ComfyUI.

This script was created to solve the main pain point of working with hundreds of LORAs: remembering exactly what a model does, what its trigger words are, and what the generated results look like, without having to check Civitai every single time.

The script scans your models folder, quickly extracts metadata, and generates an offline, visually pleasing HTML gallery complete with filters, search functionality, and a media player right in your browser. Forget about manually searching for trigger words on Civitai!

✨ Key Features
- Smart Cache (lora_database.json): The script instantly skips already processed models by verifying their exact file size. Rescanning even a terabyte-sized collection takes only seconds.
- Offline Previews: Images and videos from Civitai are automatically downloaded to the _temp/ folder. Your gallery will load instantly and work without an internet connection.
- Built-in Media Player (Popup Lightbox): Full support for .mp4 and .webm video previews. Click on any image or video to open it fullscreen along with its generation prompt.
- Dynamic Tabs: Automatic filtering of LORAs by their base model (e.g., switch between SD 1.5, SDXL, and Flux with a single click).
- Click-to-Copy: Copy long prompts and trigger words to your clipboard with a simple click.
- Direct Header Reading: The script reads metadata (Kohya SS, ModelSpec) directly from the .safetensors binary header, without loading massive model weights into RAM.
- Fail-Safe Execution: You can interrupt the process with Ctrl+C at any time — the script will save its progress and generate the gallery for the already processed models.

📦 Installation & Usage
- Download lora_indexer.py into your models directory (e.g., ComfyUI/models/loras).
- Install the requests dependency (if not installed):

pip install requests

Run the script:
python lora_indexer.py
