import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
from PIL import Image
import pytesseract
import cv2
import numpy as np
import sqlite3
import difflib
import asyncio
import time

# Настройте путь к Tesseract, если требуется
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Инициализация базы данных
def initialize_db():
    """Создает базу данных и таблицу, если они не существуют."""
    conn = sqlite3.connect("microchips.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS microchips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def add_to_database(name, description):
    """Добавляет запись в базу данных."""
    conn = sqlite3.connect("microchips.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO microchips (name, description) VALUES (?, ?)", (name, description))
    conn.commit()
    conn.close()
    log_action(f"Добавлена запись в базу данных: {name}")

def find_similar_text(input_text):
    """Ищет наиболее похожий текст в базе данных."""
    conn = sqlite3.connect("microchips.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, description FROM microchips")
    rows = cursor.fetchall()
    conn.close()

    # Поиск наиболее похожего текста
    best_match = None
    highest_ratio = 0
    for name, description in rows:
        ratio = difflib.SequenceMatcher(None, input_text, description).ratio()
        if ratio > highest_ratio:
            highest_ratio = ratio
            best_match = (name, description)

    if best_match:
        log_action(f"Найден наиболее похожий текст (похожесть: {highest_ratio:.2f}): {best_match[0]}")
        return best_match[0], best_match[1], highest_ratio
    else:
        log_action("Совпадений не найдено.")
        return None, None, 0

def preprocess_image(image_path):
    """Обрабатывает изображение для улучшения OCR."""
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        image = cv2.GaussianBlur(image, (5, 5), 0)
        _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        log_action(f"Угол поворота: {angle:.2f} градусов. Ориентация исправлена.")
        return image
    except Exception as e:
        log_error(f"Ошибка обработки изображения: {e}")
        return None

async def process_image_async():
    """Асинхронная функция для обработки изображения."""
    start_time = time.time()
    file_path = file_path_entry.get()
    selected_lang = lang_combobox.get()

    if not file_path:
        log_error("Выберите файл перед обработкой.")
        return

    try:
        processed_image = preprocess_image(file_path)
        if processed_image is None:
            log_error("Не удалось обработать изображение.")
            return

        log_action("Начинаем OCR...")
        text = pytesseract.image_to_string(processed_image, lang=selected_lang)
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, text)

        # Найти наиболее похожий текст в базе данных
        name, similar_text, similarity = find_similar_text(text)
        if name:
            result = f"Наиболее похожий текст:\nНазвание микросхемы: {name}\nОписание: {similar_text}\nПохожесть: {similarity:.2f}"
        else:
            result = "Совпадений в базе данных не найдено."
        output_text.insert(tk.END, f"\n\n{result}")

        elapsed_time = time.time() - start_time
        log_action(f"Время обработки: {elapsed_time:.2f} секунд.")
    except Exception as e:
        log_error(f"Ошибка обработки изображения: {e}")

def add_chip():
    """Открывает окно для добавления новой записи в базу данных."""
    def save_chip():
        name = name_entry.get().strip()
        description = description_text.get(1.0, tk.END).strip()
        if name and description:
            add_to_database(name, description)
            add_chip_window.destroy()
        else:
            messagebox.showerror("Ошибка", "Название и описание не могут быть пустыми.")

    add_chip_window = tk.Toplevel(window)
    add_chip_window.title("Добавить микросхему")

    tk.Label(add_chip_window, text="Название микросхемы:").pack(pady=5)
    name_entry = tk.Entry(add_chip_window, width=50)
    name_entry.pack(pady=5)

    tk.Label(add_chip_window, text="Описание:").pack(pady=5)
    description_text = scrolledtext.ScrolledText(add_chip_window, wrap=tk.WORD, width=50, height=10)
    description_text.pack(pady=5)

    tk.Button(add_chip_window, text="Сохранить", command=save_chip).pack(pady=10)

def select_file():
    """Открывает диалог выбора файла и вставляет путь в поле ввода."""
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
    if file_path:
        file_path_entry.delete(0, tk.END)
        file_path_entry.insert(0, file_path)
        log_action(f"Выбран файл: {file_path}")

def log_action(message):
    """Добавляет запись в лог."""
    log_text.insert(tk.END, f"[INFO] {time.strftime('%H:%M:%S')} - {message}\n")
    log_text.see(tk.END)

def log_error(message):
    """Добавляет запись об ошибке в лог."""
    log_text.insert(tk.END, f"[ERROR] {time.strftime('%H:%M:%S')} - {message}\n")
    log_text.see(tk.END)
    messagebox.showerror("Ошибка", message)

def start_processing():
    """Обертка для запуска асинхронной обработки."""
    asyncio.run(process_image_async())

# Создаем основное окно
window = tk.Tk()
window.title("OCR с базой данных микросхем")

# Поле для выбора файла
file_path_label = tk.Label(window, text="Путь к файлу:")
file_path_label.pack(pady=5)

file_path_entry = tk.Entry(window, width=50)
file_path_entry.pack(pady=5)

select_button = tk.Button(window, text="Выбрать файл", command=select_file)
select_button.pack(pady=5)

# Выпадающий список для выбора языка
lang_label = tk.Label(window, text="Язык распознавания:")
lang_label.pack(pady=5)

lang_combobox = ttk.Combobox(window, values=["rus", "eng", "rus+eng"], state="readonly")
lang_combobox.set("rus+eng")
lang_combobox.pack(pady=5)

# Кнопка для обработки изображения
process_button = tk.Button(window, text="Обработать изображение", command=start_processing)
process_button.pack(pady=10)

# Кнопка для добавления микросхемы
add_chip_button = tk.Button(window, text="Добавить микросхему", command=add_chip)
add_chip_button.pack(pady=5)

# Поле для вывода результата
output_label = tk.Label(window, text="Распознанный текст:")
output_label.pack(pady=5)

output_text = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=60, height=15)
output_text.pack(pady=10)

# Поле для логирования
log_label = tk.Label(window, text="Лог действий:")
log_label.pack(pady=5)

log_text = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=60, height=10, state="normal")
log_text.pack(pady=10)

# Инициализация базы данных
initialize_db()

# Запуск основного цикла
window.mainloop()
