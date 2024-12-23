import tkinter as tk
from tkinter import filedialog, scrolledtext, ttk, messagebox
from PIL import Image
import pytesseract
import cv2
import numpy as np

# Настройте путь к Tesseract, если требуется
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

def preprocess_image(image_path):
    """Обрабатывает изображение для улучшения OCR."""
    try:
        # Читаем изображение с помощью OpenCV
        image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

        # Убираем шумы с помощью GaussianBlur
        image = cv2.GaussianBlur(image, (5, 5), 0)

        # Бинаризация изображения (черно-белое изображение)
        _, image = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # Попробуем исправить ориентацию текста
        coords = np.column_stack(np.where(image > 0))
        angle = cv2.minAreaRect(coords)[-1]

        # Корректируем угол
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # Поворачиваем изображение
        (h, w) = image.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)

        log_action(f"Угол поворота: {angle:.2f} градусов. Ориентация исправлена.")
        return image
    except Exception as e:
        log_error(f"Ошибка обработки изображения: {e}")
        return None

def select_file():
    """Функция для выбора файла изображения."""
    file_path = filedialog.askopenfilename(
        filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp")]
    )
    if file_path:
        file_path_entry.delete(0, tk.END)
        file_path_entry.insert(0, file_path)
        log_action(f"Файл выбран: {file_path}")

def process_image():
    """Функция для обработки изображения и распознавания текста."""
    file_path = file_path_entry.get()
    selected_lang = lang_combobox.get()

    if not file_path:
        log_error("Выберите файл перед обработкой.")
        return

    try:
        # Предобработка изображения
        processed_image = preprocess_image(file_path)
        if processed_image is None:
            log_error("Не удалось обработать изображение.")
            return

        # Распознаём текст
        text = pytesseract.image_to_string(processed_image, lang=selected_lang)
        output_text.delete(1.0, tk.END)
        output_text.insert(tk.END, text)
        log_action("Текст успешно распознан.")
    except Exception as e:
        log_error(f"Ошибка обработки изображения: {e}")

def save_text():
    """Сохранение распознанного текста в файл."""
    text = output_text.get(1.0, tk.END).strip()
    if not text:
        log_error("Нет текста для сохранения.")
        return

    file_path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt")]
    )
    if file_path:
        try:
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(text)
            log_action(f"Текст успешно сохранён в файл: {file_path}")
        except Exception as e:
            log_error(f"Ошибка сохранения текста: {e}")

def log_action(message):
    """Добавляет запись в лог."""
    log_text.insert(tk.END, f"INFO: {message}\n")
    log_text.see(tk.END)

def log_error(message):
    """Добавляет запись об ошибке в лог."""
    log_text.insert(tk.END, f"ERROR: {message}\n")
    log_text.see(tk.END)
    messagebox.showerror("Ошибка", message)

# Создаем основное окно
window = tk.Tk()
window.title("Распознавание текста на изображении с коррекцией")

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
process_button = tk.Button(window, text="Обработать изображение", command=process_image)
process_button.pack(pady=10)

# Поле для вывода результата
output_label = tk.Label(window, text="Распознанный текст:")
output_label.pack(pady=5)

output_text = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=60, height=15)
output_text.pack(pady=10)

# Кнопка для сохранения текста
save_button = tk.Button(window, text="Сохранить текст", command=save_text)
save_button.pack(pady=5)

# Поле для логирования
log_label = tk.Label(window, text="Лог действий:")
log_label.pack(pady=5)

log_text = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=60, height=10, state="normal")
log_text.pack(pady=10)

# Запуск основного цикла
window.mainloop()
