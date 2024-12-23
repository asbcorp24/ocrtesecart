import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
from PIL import Image, ImageTk
import pytesseract
import cv2
import numpy as np
import sqlite3
import pandas as pd
from Levenshtein import ratio as levenshtein_ratio
from rapidfuzz import fuzz
import asyncio
import time
import logging

# Настройка логирования
logging.basicConfig(
    filename="microchip_processor.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Настройка Tesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'


# Инициализация базы данных
def initialize_db():
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
    conn = sqlite3.connect("microchips.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO microchips (name, description) VALUES (?, ?)", (name, description))
    conn.commit()
    conn.close()
    log_action(f"Добавлена запись в базу данных: {name}")


def preprocess_image(image_path):
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
    start_time = time.time()
    file_path = file_path_entry.get()

    if not file_path:
        log_error("Выберите файл перед обработкой.")
        return

    try:
        # Отображение изображения в интерфейсе
        display_image(file_path)

        processed_image = preprocess_image(file_path)
        if processed_image is None:
            log_error("Не удалось обработать изображение.")
            return

        log_action("Начинаем OCR...")
        text = pytesseract.image_to_string(processed_image, lang="eng+rus")
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, text)

        elapsed_time = time.time() - start_time
        log_action(f"Время обработки: {elapsed_time:.2f} секунд.")
    except Exception as e:
        log_error(f"Ошибка обработки изображения: {e}")


def display_image(image_path):
    """Отображает изображение в интерфейсе."""
    try:
        image = Image.open(image_path)
        image = image.resize((400, 300), Image.Resampling.LANCZOS)  # Используем Resampling.LANCZOS
        img_tk = ImageTk.PhotoImage(image)
        image_label.config(image=img_tk)
        image_label.image = img_tk
    except Exception as e:
        log_error(f"Ошибка отображения изображения: {e}")

def export_to_csv():
    try:
        conn = sqlite3.connect("microchips.db")
        df = pd.read_sql_query("SELECT * FROM microchips", conn)
        conn.close()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if file_path:
            df.to_csv(file_path, index=False, encoding="utf-8")
            log_action(f"База данных успешно экспортирована в файл: {file_path}")
    except Exception as e:
        log_error(f"Ошибка экспорта в CSV: {e}")


def log_action(message):
    logging.info(message)
    log_text.insert(tk.END, f"[INFO] {time.strftime('%H:%M:%S')} - {message}\n")
    log_text.see(tk.END)


def log_error(message):
    logging.error(message)
    log_text.insert(tk.END, f"[ERROR] {time.strftime('%H:%M:%S')} - {message}\n")
    log_text.see(tk.END)
    messagebox.showerror("Ошибка", message)


def select_file():
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
    if file_path:
        file_path_entry.delete(0, tk.END)
        file_path_entry.insert(0, file_path)
        log_action(f"Выбран файл: {file_path}")


def start_processing():
    asyncio.run(process_image_async())


# Интерфейс
window = tk.Tk()
window.title("OCR для микросхем")

# Создание стилей
style = ttk.Style()
style.configure("TButton", font=("Arial", 10))
style.configure("TLabel", font=("Arial", 12))

frame_top = ttk.Frame(window, padding=10)
frame_top.pack(fill=tk.X)

frame_image = ttk.Frame(window, padding=10)
frame_image.pack()

frame_bottom = ttk.Frame(window, padding=10)
frame_bottom.pack(fill=tk.BOTH, expand=True)

# Верхняя часть: выбор файла
file_path_label = ttk.Label(frame_top, text="Путь к файлу:")
file_path_label.pack(side=tk.LEFT)

file_path_entry = ttk.Entry(frame_top, width=50)
file_path_entry.pack(side=tk.LEFT, padx=5)

select_button = ttk.Button(frame_top, text="Выбрать файл", command=select_file)
select_button.pack(side=tk.LEFT)

process_button = ttk.Button(frame_top, text="Обработать", command=start_processing)
process_button.pack(side=tk.LEFT, padx=5)

# Средняя часть: отображение изображения
image_label = ttk.Label(frame_image, text="Выбранное изображение", anchor=tk.CENTER)
image_label.pack()

# Нижняя часть: вывод результата
output_label = ttk.Label(frame_bottom, text="Распознанный текст:")
output_label.pack(anchor=tk.W)

output_text = scrolledtext.ScrolledText(frame_bottom, wrap=tk.WORD, height=10)
output_text.pack(fill=tk.BOTH, expand=True)

# Лог
log_label = ttk.Label(frame_bottom, text="Лог:")
log_label.pack(anchor=tk.W)

log_text = scrolledtext.ScrolledText(frame_bottom, wrap=tk.WORD, height=8)
log_text.pack(fill=tk.BOTH, expand=True)

# Инициализация базы данных
initialize_db()

# Запуск интерфейса
window.mainloop()
