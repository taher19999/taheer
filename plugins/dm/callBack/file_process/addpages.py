# This module is part of https://github.com/nabilanavab/ilovepdf
# Feel free to use and contribute to this project. Your contributions are welcome!
# copyright © 2021 nabilanavab

file_name = "plugins/dm/callBack/file_process/addPDFPg.py"

import fitz  # PyMuPDF
from logger import logger

async def addPDFPg(main_pdf: str, page_pdf: str, position: int, add_all_pages: bool) -> (bool, str):
    """
    Insert pages from one PDF into another at a specific position.

    Parameters:
        main_pdf      : Path to the main PDF file where pages will be inserted.
        page_pdf      : Path to the PDF file containing the pages to be added.
        position      : The position (1-based index) where pages should be inserted.
        add_all_pages : If True, insert all pages from `page_pdf`, otherwise insert only the first page.

    Returns:
        bool         : Returns True if the operation is successful.
        output_path  : The path to the modified PDF file or an error message in case of failure.
    """
    try:
        output_path = f"{main_pdf}_modified.pdf"  # تحديد اسم ملف الإخراج

        # فتح الملفات
        main_doc = fitz.open(main_pdf)
        page_doc = fitz.open(page_pdf)

        # التحقق من صحة الموضع
        if position < 1 or position > len(main_doc) + 1:
            return False, "Invalid position!"

        # إدراج الصفحات الجديدة في الموضع المحدد
        if add_all_pages:
            for i in range(len(page_doc)):
                main_doc.insert_pdf(page_doc, from_page=i, to_page=i, start_at=position - 1 + i)
        else:
            main_doc.insert_pdf(page_doc, from_page=0, to_page=0, start_at=position - 1)

        # حفظ الملف المعدل
        main_doc.save(output_path)
        main_doc.close()
        page_doc.close()

        return True, output_path

    except Exception as Error:
        logger.exception("⚠ %s: %s" % (file_name, Error), exc_info=True)
        return False, str(Error)
