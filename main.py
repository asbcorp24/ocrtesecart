import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
from PIL import Image, ImageTk
import pytesseract
import easyocr
import cv2
import numpy as np
import sqlite3
import pandas as pd
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
pytesseract.pytesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Настройка EasyOCR
reader = easyocr.Reader(['en', 'ru'], gpu=False)


# Работа с базой данных
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


def export_to_csv():
    """Экспортирует базу данных в файл CSV."""
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


def export_to_excel():
    """Экспортирует базу данных в файл Excel."""
    try:
        conn = sqlite3.connect("microchips.db")
        df = pd.read_sql_query("SELECT * FROM microchips", conn)
        conn.close()

        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
        )
        if file_path:
            df.to_excel(file_path, index=False, engine="openpyxl")
            log_action(f"База данных успешно экспортирована в файл: {file_path}")
    except Exception as e:
        log_error(f"Ошибка экспорта в Excel: {e}")


# Предобработка изображения
def preprocess_image(image_path):
    """Предобработка изображения для OCR."""
    try:
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
        image = cv2.GaussianBlur(image, (5, 5), 0)
        _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        return binary
    except Exception as e:
        log_error(f"Ошибка предобработки изображения: {e}")
        return None


async def process_image_with_tesseract(image_path):
    """Обработка изображения с использованием Tesseract OCR."""
    try:
        binary_image = preprocess_image(image_path)
        if binary_image is None:
            return "Ошибка предобработки изображения."

        text = pytesseract.image_to_string(binary_image, lang="eng+rus")
        return text.strip()
    except Exception as e:
        log_error(f"Ошибка Tesseract OCR: {e}")
        return "Ошибка Tesseract OCR."


async def process_image_with_easyocr(image_path):
    """Обработка изображения с использованием EasyOCR."""
    try:
        results = reader.readtext(image_path, detail=0)  # detail=0 возвращает только текст
        return "\n".join(results)
    except Exception as e:
        log_error(f"Ошибка EasyOCR: {e}")
        return "Ошибка EasyOCR."


async def process_image_async():
    """Основная функция обработки изображения с выбором OCR."""
    file_path = file_path_entry.get()

    if not file_path:
        log_error("Выберите файл перед обработкой.")
        return

    try:
        # Отображение изображения
        display_image(file_path)

        # Определение выбранного OCR
        selected_ocr = ocr_combobox.get()
        log_action(f"Выбран метод OCR: {selected_ocr}")

        if selected_ocr == "Tesseract":
            text = await process_image_with_tesseract(file_path)
        elif selected_ocr == "EasyOCR":
            text = await process_image_with_easyocr(file_path)
        else:
            text = "Неизвестный метод OCR."

        # Вывод результата
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, text)

    except Exception as e:
        log_error(f"Ошибка обработки изображения: {e}")


def display_image(image_path):
    """Отображает изображение в интерфейсе."""
    try:
        image = Image.open(image_path)
        image = image.resize((400, 300), Image.Resampling.LANCZOS)
        img_tk = ImageTk.PhotoImage(image)
        image_label.config(image=img_tk)
        image_label.image = img_tk
    except Exception as e:
        log_error(f"Ошибка отображения изображения: {e}")


def log_action(message):
    """Логирует действие."""
    logging.info(message)
    log_text.insert(tk.END, f"[INFO] {time.strftime('%H:%M:%S')} - {message}\n")
    log_text.see(tk.END)


def log_error(message):
    """Логирует ошибку."""
    logging.error(message)
    log_text.insert(tk.END, f"[ERROR] {time.strftime('%H:%M:%S')} - {message}\n")
    log_text.see(tk.END)
    messagebox.showerror("Ошибка", message)


def select_file():
    """Выбор файла изображения."""
    file_path = filedialog.askopenfilename(filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
    if file_path:
        file_path_entry.delete(0, tk.END)
        file_path_entry.insert(0, file_path)
        log_action(f"Выбран файл: {file_path}")


def start_processing():
    """Запуск асинхронной обработки изображения."""
    asyncio.run(process_image_async())


# Интерфейс
window = tk.Tk()
window.title("OCR для микросхем")

# Верхняя часть
frame_top = ttk.Frame(window, padding=10)
frame_top.pack(fill=tk.X)

file_path_label = ttk.Label(frame_top, text="Путь к файлу:")
file_path_label.pack(side=tk.LEFT)

file_path_entry = ttk.Entry(frame_top, width=50)
file_path_entry.pack(side=tk.LEFT, padx=5)

select_button = ttk.Button(frame_top, text="Выбрать файл", command=select_file)
select_button.pack(side=tk.LEFT)

ocr_combobox = ttk.Combobox(frame_top, values=["Tesseract", "EasyOCR"], state="readonly")
ocr_combobox.set("Tesseract")
ocr_combobox.pack(side=tk.LEFT, padx=5)

process_button = ttk.Button(frame_top, text="Обработать", command=start_processing)
process_button.pack(side=tk.LEFT, padx=5)

# Кнопки экспорта
export_csv_button = ttk.Button(frame_top, text="Экспорт в CSV", command=export_to_csv)
export_csv_button.pack(side=tk.LEFT, padx=5)

export_excel_button = ttk.Button(frame_top, text="Экспорт в Excel", command=export_to_excel)
export_excel_button.pack(side=tk.LEFT, padx=5)

# Средняя часть
frame_image = ttk.Frame(window, padding=10)
frame_image.pack()

image_label = ttk.Label(frame_image, text="Выбранное изображение", anchor=tk.CENTER)
image_label.pack()

# Нижняя часть
frame_bottom = ttk.Frame(window, padding=10)
frame_bottom.pack(fill=tk.BOTH, expand=True)

output_label = ttk.Label(frame_bottom, text="Распознанный текст:")
output_label.pack(anchor=tk.W)

output_text = scrolledtext.ScrolledText(frame_bottom, wrap=tk.WORD, height=10)
output_text.pack(fill=tk.BOTH, expand=True)

log_label = ttk.Label(frame_bottom, text="Лог:")
log_label.pack(anchor=tk.W)

log_text = scrolledtext.ScrolledText(frame_bottom, wrap=tk.WORD, height=8)
log_text.pack(fill=tk.BOTH, expand=True)

# Инициализация базы данных
initialize_db()

# Запуск интерфейса
window.mainloop()
