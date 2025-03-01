# ملف plugins/dm/callBack/file_process/addpg.py

from pyrogram import filters, enums, Client
from pyrogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    Message,
    CallbackQuery
)
from plugins import *
from plugins.utils import *
from PyPDF2 import PdfReader, PdfWriter
import os, logging, asyncio

# تخزين بيانات المستخدمين
user_states = {}

# بدء المحادثة
@ILovePDF.on_message(filters.command("addpages") & filters.private)
async def start_add_pages(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        user_states[user_id] = {"step": "main_pdf"}
        
        # الحصول على اللغة المحددة
        lang_code = await util.getLang(user_id)
        tTXT = await util.translate(text="SEND_MAIN_PDF", lang_code=lang_code)
        
        # إرسال رسالة الترحيب
        await message.reply_text(tTXT)
        await message.delete()
        
    except Exception as e:
        logger.exception(f"📌 addpages.start: {e}")

# معالجة الملفات المرسلة
@ILovePDF.on_message(filters.document & filters.private)
async def handle_documents(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        state = user_states.get(user_id, {})
        
        if not state:
            return
        
        # التأكد من أن الملف هو PDF
        if message.document.mime_type != "application/pdf":
            lang_code = await util.getLang(user_id)
            tTXT = await util.translate(text="PDF_ONLY", lang_code=lang_code)
            return await message.reply_text(tTXT)
        
        if state["step"] == "main_pdf":
            # حفظ الملف الرئيسي
            file_path = await message.download(f"work/{user_id}_main.pdf")
            user_states[user_id].update({
                "main_file": file_path,
                "step": "add_pages"
            })
            
            # إعداد لوحة المفاتيح
            lang_code = await util.getLang(user_id)
            tTXT = await util.translate(text="MAIN_PDF_RECEIVED", lang_code=lang_code)
            keyboard = [[
                InlineKeyboardButton("➕ إضافة صفحة", callback_data="add_page")
            ]]
            
            # إرسال الرسالة مع لوحة المفاتيح
            await message.reply_text(
                tTXT,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        elif state["step"] == "add_pages":
            # حفظ ملف الصفحات
            file_path = await message.download(f"work/{user_id}_pages.pdf")
            user_states[user_id].update({
                "pages_file": file_path,
                "step": "choose_option"
            })
            
            # إعداد لوحة المفاتيح
            lang_code = await util.getLang(user_id)
            tTXT = await util.translate(text="CHOOSE_OPTION", lang_code=lang_code)
            keyboard = [[
                InlineKeyboardButton("📄 الكل", callback_data="all_pages"),
                InlineKeyboardButton("📑 واحدة", callback_data="single_page")
            ]]
            
            # إرسال الرسالة مع لوحة المفاتيح
            await message.reply_text(
                tTXT,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
    except Exception as e:
        logger.exception(f"📌 addpages.doc_handler: {e}")

# معالجة الأزرار
@ILovePDF.on_callback_query(filters.regex(r"^(add_page|all_pages|single_page)$"))
async def handle_buttons(client: Client, callback_query: CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        data = callback_query.data
        
        if data == "add_page":
            lang_code = await util.getLang(user_id)
            tTXT = await util.translate(text="SEND_PAGES", lang_code=lang_code)
            await callback_query.edit_message_text(tTXT)
        
        elif data in ["all_pages", "single_page"]:
            user_states[user_id]["add_all"] = (data == "all_pages")
            user_states[user_id]["step"] = "get_position"
            
            lang_code = await util.getLang(user_id)
            tTXT = await util.translate(text="SEND_POSITION", lang_code=lang_code)
            await callback_query.edit_message_text(tTXT)
        
    except Exception as e:
        logger.exception(f"📌 addpages.button_handler: {e}")

# معالجة رقم الموضع
@ILovePDF.on_message(filters.text & filters.private)
async def handle_position(client: Client, message: Message):
    try:
        user_id = message.from_user.id
        state = user_states.get(user_id, {})
        
        if state.get("step") != "get_position":
            return
        
        if not message.text.isdigit():
            lang_code = await util.getLang(user_id)
            tTXT = await util.translate(text="INTEGER_ONLY", lang_code=lang_code)
            return await message.reply_text(tTXT)
        
        position = int(message.text) - 1
        
        # معالجة الملفات
        main_pdf = PdfReader(state["main_file"])
        pages_pdf = PdfReader(state["pages_file"])
        writer = PdfWriter()
        
        # إضافة الصفحات حتى الموضع المحدد
        for i in range(position):
            writer.add_page(main_pdf.pages[i])
        
        # إضافة الصفحات الجديدة
        if state.get("add_all", False):
            for page in pages_pdf.pages:
                writer.add_page(page)
        else:
            writer.add_page(pages_pdf.pages[0])
        
        # إضافة بقية الصفحات
        for i in range(position, len(main_pdf.pages)):
            writer.add_page(main_pdf.pages[i])
        
        # حفظ الملف النهائي
        output_file = f"work/{user_id}_modified.pdf"
        with open(output_file, "wb") as f:
            writer.write(f)
        
        # إرسال الملف النهائي
        lang_code = await util.getLang(user_id)
        tTXT = await util.translate(text="SUCCESS_MESSAGE", lang_code=lang_code)
        await message.reply_document(output_file, caption=tTXT)
        
        # تنظيف الملفات المؤقتة
        for file in [state["main_file"], state["pages_file"], output_file]:
            if os.path.exists(file):
                os.remove(file)
        
        del user_states[user_id]
        
    except Exception as e:
        logger.exception(f"📌 addpages.position_handler: {e}")

# تشغيل البوت
async def main():
    await ILovePDF.start()
    await ILovePDF.run()

if __name__ == "__main__":
    asyncio.run(main())
