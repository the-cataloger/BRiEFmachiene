```python
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image
from PyPDF2 import PdfMerger
import tempfile
import glob
import logging
from natsort import natsorted

# إعداد السجل لتتبع العمليات
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_pdf_from_images(images, pdf_path):
    """
    إنشاء ملف PDF من قائمة الصور.
    
    Args:
        images (list): قائمة بمسارات ملفات الصور.
        pdf_path (str): مسار ملف PDF الناتج.
    
    Returns:
        bool: True إذا تم إنشاء PDF بنجاح، False عكس ذلك.
    """
    if not images:
        logging.warning(f"لم يتم تقديم صور لإنشاء PDF: {pdf_path}")
        return False

    pdf_merger = PdfMerger()
    temp_files = []
    try:
        for image_file in images:
            with Image.open(image_file) as image:
                # تحويل الصورة إلى RGB إذا لزم الأمر (لدعم PNG مع الشفافية)
                if image.mode in ('RGBA', 'LA'):
                    image = image.convert('RGB')
                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
                    image.save(temp_pdf, "PDF", resolution=100.0)
                    temp_files.append(temp_pdf.name)
                    pdf_merger.append(temp_pdf.name)
        
        # التأكد من وجود صفحات للدمج
        if temp_files:
            with open(pdf_path, 'wb') as output_pdf:
                pdf_merger.write(output_pdf)
            logging.info(f"تم إنشاء PDF: {pdf_path}")
            return True
        else:
            logging.warning(f"لا توجد صور صالحة لإنشاء PDF: {pdf_path}")
            return False
    except Exception as e:
        logging.error(f"خطأ أثناء إنشاء PDF {pdf_path}: {e}")
        return False
    finally:
        # تنظيف الملفات المؤقتة
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except Exception as e:
                logging.warning(f"فشل في حذف الملف المؤقت {temp_file}: {e}")
        pdf_merger.close()

def process_directory(directory, destination_path, images_per_pdf=6):
    """
    معالجة المجلدات الفرعية وإنشاء ملفات PDF من الصور.
    
    Args:
        directory (str): مسار المجلد الرئيسي.
        destination_path (str): مسار المجلد الوجهة لملفات PDF.
        images_per_pdf (int): عدد الصور لكل PDF (افتراضي: 3 من البداية + 3 من النهاية).
    
    Returns:
        bool: True إذا تمت معالجة أي مجلد بنجاح، False عكس ذلك.
    """
    if not os.path.isdir(directory):
        logging.error(f"المجلد غير صالح: {directory}")
        return False

    os.makedirs(destination_path, exist_ok=True)
    success_count = 0
    for root, dirs, _ in os.walk(directory):
        for dir_name in dirs:
            dir_path = os.path.join(root, dir_name)
            # دعم تنسيقات صور متعددة
            image_files = natsorted(
                glob.glob(os.path.join(dir_path, '*.jpg')) +
                glob.glob(os.path.join(dir_path, '*.jpeg')) +
                glob.glob(os.path.join(dir_path, '*.png'))
            )

            if not image_files:
                logging.info(f"لم يتم العثور على صور في {dir_path}")
                continue

            # اختيار الصور: الكل إذا كان العدد أقل من images_per_pdf، وإلا الأولى والأخيرة
            if len(image_files) < images_per_pdf:
                selected_images = image_files
                logging.warning(f"عدد الصور في {dir_name} أقل من {images_per_pdf}. سيتم استخدام الكل.")
            else:
                half = images_per_pdf // 2
                selected_images = image_files[:half] + image_files[-half:]
            
            final_pdf_path = os.path.join(destination_path, f"{dir_name}.pdf")

            try:
                if create_pdf_from_images(selected_images, final_pdf_path):
                    success_count += 1
                else:
                    logging.warning(f"فشل في إنشاء PDF لـ {dir_name}")
            except Exception as e:
                logging.error(f"خطأ أثناء معالجة {dir_name}: {e}")

    logging.info(f"تمت معالجة {success_count} مجلدات بنجاح")
    return success_count > 0

def browse_directory():
    """فتح نافذة لاختيار المجلد الرئيسي."""
    directory = filedialog.askdirectory()
    if directory:
        source_entry.delete(0, tk.END)
        source_entry.insert(0, directory)

def browse_output_folder():
    """فتح نافذة لاختيار مجلد الوجهة."""
    folder_path = filedialog.askdirectory()
    if folder_path:
        output_entry.delete(0, tk.END)
        output_entry.insert(0, folder_path)

def create_pdfs():
    """معالجة إنشاء ملفات PDF بناءً على مدخلات الواجهة."""
    source_dir = source_entry.get()
    output_folder = output_entry.get()
    try:
        images_per_pdf = int(num_files_spinbox.get()) * 2  # ضعف العدد لتغطية البداية والنهاية
    except ValueError:
        messagebox.showerror("خطأ", "يرجى إدخال عدد صالح للصور.")
        return

    # التحقق من صحة المدخلات
    if not source_dir or not os.path.isdir(source_dir):
        messagebox.showerror("خطأ", "يرجى اختيار مجلد رئيسي صالح.")
        return
    if not output_folder:
        messagebox.showerror("خطأ", "يرجى اختيار مجلد وجهة.")
        return
    if not os.access(output_folder, os.W_OK):
        messagebox.showerror("خطأ", "لا توجد صلاحيات كتابة لمجلد الوجهة.")
        return

    # إظهار مؤشر التقدم
    app.config(cursor="wait")
    create_button.config(state="disabled")
    app.update()

    try:
        # معالجة المجلد
        if process_directory(source_dir, output_folder, images_per_pdf):
            messagebox.showinfo("نجاح", "تم إنشاء ملفات PDF بنجاح!")
        else:
            messagebox.showwarning("تحذير", "لم يتم إنشاء أي ملفات PDF. تحقق من السجلات.")
    except Exception as e:
        messagebox.showerror("خطأ", f"حدث خطأ: {e}")
    finally:
        app.config(cursor="")
        create_button.config(state="normal")

# إعداد الواجهة الرسومية
app = tk.Tk()
app.title("BRIEF Machine")
app.geometry("600x250")

# مكونات الواجهة
tk.Label(app, text="المجلد الرئيسي:").grid(row=0, column=0, padx=10, pady=10, sticky="e")
source_entry = tk.Entry(app, width=50)
source_entry.grid(row=0, column=1, padx=10, pady=10)
tk.Button(app, text="استعراض", command=browse_directory).grid(row=0, column=2, padx=10, pady=10)

tk.Label(app, text="مجلد الوجهة:").grid(row=1, column=0, padx=10, pady=10, sticky="e")
output_entry = tk.Entry(app, width=50)
output_entry.grid(row=1, column=1, padx=10, pady=10)
tk.Button(app, text="استعراض", command=browse_output_folder).grid(row=1, column=2, padx=10, pady=10)

tk.Label(app, text="عدد الصور لكل PDF (نصف من البداية، نصف من النهاية):").grid(row=2, column=0, padx=10, pady=10, sticky="e")
num_files_spinbox = tk.Spinbox(app, from_=1, to=100, width=10)
num_files_spinbox.grid(row=2, column=1, padx=10, pady=10, sticky="w")
num_files_spinbox.delete(0, tk.END)
num_files_spinbox.insert(0, "3")  # القيمة الافتراضية

create_button = tk.Button(app, text="إنشاء ملفات PDF", command=create_pdfs)
create_button.grid(row=3, column=1, pady=20)

# تشغيل التطبيق
app.mainloop()
```