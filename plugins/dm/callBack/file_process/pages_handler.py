import os
import logging
from tempfile import NamedTemporaryFile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from PyPDF2 import PdfReader, PdfWriter

# تعريف حالات المحادثة
MAIN_PDF, PAGE_PDF, CHOOSE_OPTION, POSITION = range(4)

async def addpages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🖨️ أرسل الملف الرئيسي (PDF) الآن:")
    return MAIN_PDF

async def handle_main_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if document.mime_type != "application/pdf":
        await update.message.reply_text("❌ يُرجى إرسال ملف PDF فقط!")
        return MAIN_PDF

    file = await document.get_file()
    file_name = document.file_name
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        await file.download_to_memory(temp)
        context.user_data["main_pdf"] = temp.name
        context.user_data["file_name"] = file_name

    keyboard = [[InlineKeyboardButton("➕ إضافة صفحة", callback_data="add_page")]]
    await update.message.reply_text(
        "✅ تم استلام الملف الرئيسي!\n\nاختر الإجراء:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PAGE_PDF

async def handle_page_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("📤 أرسل ملف الصفحة/الصفحات الآن:")
    else:
        await update.message.reply_text("📤 أرسل ملف الصفحة/الصفحات الآن:")
    return PAGE_PDF

async def process_page_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document

    if document.mime_type != "application/pdf":
        await update.message.reply_text("❌ يُرجى إرسال ملف PDF فقط!")
        return PAGE_PDF

    file = await document.get_file()
    with NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
        await file.download_to_memory(temp)
        context.user_data["page_to_add"] = temp.name

    page_pdf = PdfReader(context.user_data["page_to_add"])
    if len(page_pdf.pages) > 1:
        keyboard = [
            [InlineKeyboardButton("📄 جميع الصفحات", callback_data="add_all")],
            [InlineKeyboardButton("📑 صفحة واحدة", callback_data="add_one")]
        ]
        await update.message.reply_text(
            "📂 يحتوي الملف على عدة صفحات!\nاختر طريقة الإضافة:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return CHOOSE_OPTION
    else:
        await update.message.reply_text("🔢 أرسل رقم الموضع (مثال: 3):")
        return POSITION

async def handle_option(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "add_all":
        context.user_data["add_all_pages"] = True
        await query.edit_message_text("🌟 سيتم إضافة جميع الصفحات!\n\n🔢 أرسل رقم الموضع (مثال: 2):")
    else:
        context.user_data["add_all_pages"] = False
        await query.edit_message_text("✨ سيتم إضافة الصفحة الأولى فقط!\n\n🔢 أرسل رقم الموضع (مثال: 2):")
    
    return POSITION

async def handle_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text

    if not text.isdigit():
        await update.message.reply_text("❌ يُرجى إرسال رقم صحيح!")
        return POSITION

    position = int(text) - 1

    try:
        main_pdf = PdfReader(context.user_data["main_pdf"])
        page_pdf = PdfReader(context.user_data["page_to_add"])
        writer = PdfWriter()

        # إضافة الصفحات قبل الموضع المطلوب
        for i in range(position):
            writer.add_page(main_pdf.pages[i])
        
        # إضافة الصفحة أو الصفحات الجديدة
        if context.user_data.get("add_all_pages", False):
            for page in page_pdf.pages:
                writer.add_page(page)
        else:
            writer.add_page(page_pdf.pages[0])
        
        # إضافة باقي الصفحات من الملف الرئيسي
        for i in range(position, len(main_pdf.pages)):
            writer.add_page(main_pdf.pages[i])

        # حفظ الملف الجديد وإرساله للمستخدم
        output_file = NamedTemporaryFile(suffix=".pdf", delete=False)
        with open(output_file.name, "wb") as f:
            writer.write(f)
        
        await update.message.reply_document(
            document=open(output_file.name, "rb"),
            filename=context.user_data["file_name"]
        )

    except Exception as e:
        logging.error(f"Error: {str(e)}")
        await update.message.reply_text("⚠️ حدث خطأ أثناء المعالجة!")

    finally:
        # تنظيف الملفات المؤقتة
        for key in ["main_pdf", "page_to_add"]:
            if key in context.user_data and os.path.exists(context.user_data[key]):
                os.unlink(context.user_data[key])
        context.user_data.clear()
        
        if 'output_file' in locals() and os.path.exists(output_file.name):
            os.unlink(output_file.name)

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for key in ["main_pdf", "page_to_add"]:
        if key in context.user_data and os.path.exists(context.user_data[key]):
            os.unlink(context.user_data[key])
    context.user_data.clear()
    
    await update.message.reply_text("🗑️ تم الإلغاء بنجاح!")
    return ConversationHandler.END

# إنشاء ConversationHandler الخاص بإضافة الصفحات
pages_conv_handler = ConversationHandler(
    entry_points=[CommandHandler("addpages", addpages)],
    states={
        MAIN_PDF: [MessageHandler(filters.Document.PDF, handle_main_pdf)],
        PAGE_PDF: [
            CallbackQueryHandler(handle_page_pdf, pattern="^add_page$"),
            MessageHandler(filters.Document.PDF, process_page_file)
        ],
        CHOOSE_OPTION: [CallbackQueryHandler(handle_option, pattern="^(add_all|add_one)$")],
        POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_position)]
    },
    fallbacks=[CommandHandler("cancel", cancel)]
)
