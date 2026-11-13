# locales/lexicon.py

"""
Barcha foydalanuvchiga ko‘rinadigan statik matnlar
uch tilda jamlangan yagona lug‘at (i18n).
"""

LEXICON: dict[str, dict[str, str]] = {
    # ---------- Общие / Используемые в разных местах ----------
    "back_button": {"uz": "⬅️ Orqaga", "ru": "⬅️ Назад", "en": "⬅️ Back"},
    "partnership_button": {"uz": "🤝 Hamkorlik", "ru": "🤝 Сотрудничество", "en": "🤝 Partnership"},
    "no_photo_warning": {
        "uz": "Iltimos, foto yuboring.",
        "ru": "Пожалуйста, пришлите фото.",
        "en": "Please send a photo.",
    },
    # ---------- /start и меню ----------
    # Ключи 'restaurant_list_title' и 'restaurant_list_empty' удалены, так как больше нет списка ресторанов.
    # Ключ 'super_admin_welcome' удален, так как роль Супер-Админа упразднена.
    "admin_welcome": {
        "uz": "Admin paneliga xush kelibsiz!",
        "ru": "Добро пожаловать в панель администратора!",
        "en": "Welcome to the admin panel!",
    },
    # ---------- Клиент — Категории ----------
    "category_list_title": {
        "uz": "📂 Kategoriyalar ro‘yxati:",
        "ru": "📂 Список категорий:",
        "en": "📂 Categories list:",
    },
    "category_empty_msg": {
        "uz": "Bu bo‘limda hozircha hech narsa yo‘q.",
        "ru": "В этом разделе пока ничего нет.",
        "en": "Nothing here yet.",
    },
    "subcategory_title_tpl": {
        "uz": "📂 <b>{name}</b> tarkibi:",
        "ru": "📂 Содержимое <b>{name}</b>:",
        "en": "📂 <b>{name}</b> contents:",
    },
    # ---------- Клиент — Продукт ----------
    "add_to_cart_button": {"uz": "➕ Savatga qo‘shish", "ru": "➕ В корзину", "en": "➕ Add to cart"},
    "price_label": {"uz": "Narx: ", "ru": "Цена: ", "en": "Price: "},
    "product_not_found": {"uz": "Mahsulot topilmadi!", "ru": "Товар не найден!", "en": "Product not found!"},
    # ---------- Ключи Супер-Админа удалены ----------
    # "sa_add_restaurant", "sa_list_restaurants", "sa_process_cancelled",
    # "sa_restaurant_added_tpl", "sa_restaurant_deleted_tpl" удалены.
    # ---------- Панель администратора — кнопки ----------
    "admin_manage_cats_btn": {
        "uz": "🗂 Kategoriyalarni boshqarish",
        "ru": "🗂 Управление категориями",
        "en": "🗂 Manage categories",
    },
    "add_category_btn": {"uz": "➕ Kategoriya qo‘shish", "ru": "➕ Добавить категорию", "en": "➕ Add category"},
    "add_subcategory_btn": {
        "uz": "➕ Ichki kategoriya qo'shish",
        "ru": "➕ Добавить подкатегорию",
        "en": "➕ Add sub-category",
    },
    "add_product_btn": {"uz": "➕ Mahsulot qo‘shish", "ru": "➕ Добавить товар", "en": "➕ Add product"},
    "list_products_btn": {"uz": "📋 Mahsulotlar ro'yxati", "ru": "📋 Список товаров", "en": "📋 Products list"},
    "edit_name_btn": {"uz": "✏️ Nomini tahrirlash", "ru": "✏️ Изменить название", "en": "✏️ Edit name"},
    "delete_btn": {"uz": "🗑 O'chirish", "ru": "🗑 Удалить", "en": "🗑 Delete"},
    # ---------- Admin panel — boshqa matnlar ----------
    "category_added_success": {
        "uz": "✅ Kategoriya muvaffiyatli qo‘shildi!",
        "ru": "✅ Категория успешно добавлена!",
        "en": "✅ Category added successfully!",
    },
    "category_deleted_success": {
        "uz": "🗑 Kategoriya muvaffiyatli o‘chirildi!",
        "ru": "🗑 Категория успешно удалена!",
        "en": "🗑 Category deleted successfully!",
    },
    "product_added_success": {
        "uz": "✅ Mahsulot muvaffiyatli qo‘shildi!",
        "ru": "✅ Товар успешно добавлен!",
        "en": "✅ Product added successfully!",
    },
    "product_deleted_success": {"uz": "🗑 O‘chirildi!", "ru": "🗑 Удалено!", "en": "🗑 Deleted!"},
    "price_only_number": {
        "uz": "❌ Narx faqat son bo‘lishi kerak. Qayta kiriting.",
        "ru": "❌ Цена должна быть числом. Попробуйте снова.",
        "en": "❌ Price must be a number. Try again.",
    },
    "price_updated": {"uz": "✅ Narx yangilandi!", "ru": "✅ Цена обновлена!", "en": "✅ Price updated!"},
    "name_updated": {
        "uz": "✅ Mahsulot nomi yangilandi!",
        "ru": "✅ Название товара обновлено!",
        "en": "✅ Product name updated!",
    },
    "photo_updated": {"uz": "✅ Rasm yangilandi!", "ru": "✅ Фото обновлено!", "en": "✅ Photo updated!"},
    "description_updated": {
        "uz": "✅ Tavsif yangilandi!",
        "ru": "✅ Описание обновлено!",
        "en": "✅ Description updated!",
    },
    "change_language_button": {"uz": "🌐 Tilni tanlash", "ru": "🌐 Выбор языка", "en": "🌐 Change language"},
    # ---------- So‘rov (prompt) matnlari ----------
    "ask_for_cat_name_tpl": {
        "uz": "{lang} tilida kategoriya nomini kiriting:",
        "ru": "Введите название категории на {lang}:",
        "en": "Enter category name in {lang}:",
    },
    "ask_for_subcat_name_tpl": {
        "uz": "{lang} tilida ichki kategoriya nomini kiriting:",
        "ru": "Введите название подкатегории на {lang}:",
        "en": "Enter sub-category name in {lang}:",
    },
    "ask_for_new_cat_name_tpl": {
        "uz": "{lang} tilida yangi nomni kiriting:",
        "ru": "Введите новое название на {lang}:",
        "en": "Enter new name in {lang}:",
    },
    "ask_for_product_name_tpl": {
        "uz": "{lang} tilida mahsulot nomini kiriting:",
        "ru": "Введите название товара на {lang}:",
        "en": "Enter product name in {lang}:",
    },
    "ask_for_product_photo": {
        "uz": "📸 Mahsulot fotosini yuboring:",
        "ru": "📸 Отправьте фото товара:",
        "en": "📸 Send the product photo:",
    },
    "ask_for_product_desc_tpl": {
        "uz": "{lang} tilida tavsif kiriting yoki ⏭️ yuborib o‘tkazing:",
        "ru": "Введите описание на {lang} или отправьте ⏭️ чтобы пропустить:",
        "en": "Enter description in {lang} or send ⏭️ to skip:",
    },
    "ask_for_price": {
        "uz": "💰 Narxni kiriting (masalan, 19999.99):",
        "ru": "💰 Введите цену (например, 19999.99):",
        "en": "💰 Enter price (e.g. 19999.99):",
    },
    "ask_for_new_price": {
        "uz": "💰 Yangi narxni kiriting (masalan, 12345.67):",
        "ru": "💰 Введите новую цену (например, 12345.67):",
        "en": "💰 Enter new price (e.g. 12345.67):",
    },
    "ask_for_new_prod_name_tpl": {
        "uz": "{lang} tilida yangi nomni kiriting:",
        "ru": "Введите новое название на {lang}:",
        "en": "Enter new name in {lang}:",
    },
    "ask_for_new_photo": {
        "uz": "🖼 Yangi mahsulot fotosini yuboring:",
        "ru": "🖼 Отправьте новое фото товара:",
        "en": "🖼 Send new product photo:",
    },
    # ---------- Tugma matnlari (qo‘shimcha) ----------
    "edit_price_btn": {"uz": "💰 Narxni tahrirlash", "ru": "💰 Изм. цену", "en": "💰 Edit price"},
    "edit_photo_btn": {"uz": "🖼 Rasmni o‘zgartirish", "ru": "🖼 Изм. фото", "en": "🖼 Edit photo"},
    "add_desc_btn": {"uz": "➕ Tavsif qo‘shish", "ru": "➕ Добавить опис.", "en": "➕ Add desc."},
    "edit_desc_btn": {"uz": "✏️ Tavsifni tahrirlash", "ru": "✏️ Изм. опис.", "en": "✏️ Edit desc."},
    # ---------- Xatolik / alert ----------
    "confirm_delete_tpl": {
        "uz": "⚠️ “{name}” ni o‘chirishga ishonchingiz komilmi?",
        "ru": "⚠️ Удалить «{name}»?",
        "en": "⚠️ Delete “{name}”?",
    },
    "language_set_alert": {"uz": "✅ Til o‘rnatildi!", "ru": "✅ Язык установлен!", "en": "✅ Language set!"},
    # ---------- Super Admin uchun kalitlar olib tashlandi ----------
    # "sa_only_superadmin", "sa_step1_enter_name", "sa_step2_enter_langs",
    # "sa_enter_at_least_one_lang", "sa_step3_enter_admin_id", "edit_rest_langs_btn",
    # "change_admin_btn", "deactivate_btn", "activate_btn", "active_label",
    # "inactive_label", "restaurant_not_found", "confirm_delete_restaurant_tpl",
    # "restaurant_already_deleted", "sa_manage_rest_tpl", "sa_prompt_new_name_tpl",
    # "name_empty_error", "sa_restaurant_name_updated_tpl", "sa_prompt_new_langs_tpl",
    # "sa_langs_updated", "sa_prompt_new_admin_id_tpl", "sa_admin_updated",
    # "sa_updated_menu_tpl" kabi barcha kalitlar loyihadan chiqarib tashlandi.
    # Umumiy xatoliklar saqlab qolindi
    "invalid_id_error": {
        "uz": "❌ ID faqat raqamlardan iborat bo‘lishi kerak. Qayta kiriting.",
        "ru": "❌ ID должен состоять только из цифр. Попробуйте ещё раз.",
        "en": "❌ ID must contain digits only. Try again.",
    },
    "db_error": {
        "uz": "❌ Bazaga yozishda xatolik yuz berdi. Keyinroq urinib ko‘ring.",
        "ru": "❌ Ошибка записи в базу. Попробуйте позже.",
        "en": "❌ Database write error. Try again later.",
    },
    "status_updated": {"uz": "Holat yangilandi.", "ru": "Статус обновлён.", "en": "Status updated."},
    "product_added_to_cart_tpl": {
        "uz": "✅ “{name}” savatga qo‘shildi!",
        "ru": "✅ «{name}» добавлен в корзину!",
        "en": "✅ “{name}” added to cart!",
    },
    "cart_button": {"uz": "🛒 Savatcha", "ru": "🛒 Корзина", "en": "🛒 Cart"},
    "view_cart_title": {"uz": "<b>🛒 Savatchangiz</b>:", "ru": "<b>🛒 Ваша корзина</b>:", "en": "<b>🛒 Your cart</b>:"},
    "cart_item_template": {
        "uz": "{name} × {quantity} = {total_sum}",
        "ru": "{name} × {quantity} = {total_sum}",
        "en": "{name} × {quantity} = {total_sum}",
    },
    "total_price": {"uz": "Umumiy: <b>{total}</b>", "ru": "Итого: <b>{total}</b>", "en": "Total: <b>{total}</b>"},
    "cart_empty": {"uz": "🛒 Savatcha bo‘sh.", "ru": "🛒 Корзина пуста.", "en": "🛒 Cart is empty."},
    "clear_cart_button": {"uz": "🗑 Savatni tozalash", "ru": "🗑 Очистить", "en": "🗑 Clear"},
    "cart_cleared_alert": {"uz": "✅ Savat tozalandi!", "ru": "✅ Корзина очищена!", "en": "✅ Cart cleared!"},
    "place_order_button": {"uz": "✅ Buyurtma berish", "ru": "✅ Оформить заказ", "en": "✅ Place order"},
    "ask_for_phone": {
        "uz": "📞 Iltimos, pastdagi tugma orqali kontaktingizni yuboring YOKI telefon raqamingizni +998... formatida yozing:",
        "ru": "📞 Пожалуйста, поделитесь контактом кнопкой ниже ИЛИ введите номер в формате +998...:",
        "en": "📞 Please share your contact with the button below OR type your phone number in +998... format:",
    },
    "send_phone_button": {
        "uz": "📞 Telefon raqamni yuborish",
        "ru": "📞 Отправить телефон",
        "en": "📞 Send phone number",
    },
    "invalid_phone_format": {
        "uz": "❌ Telefon raqami noto‘g‘ri formatda. Qayta urinib ko‘ring.",
        "ru": "❌ Неверный формат телефона. Попробуйте ещё раз.",
        "en": "❌ Invalid phone format. Please try again.",
    },
    "cart_is_empty_error": {
        "uz": "❌ Savatchangiz bo‘sh.",
        "ru": "❌ Ваша корзина пуста.",
        "en": "❌ Your cart is empty.",
    },
    "ask_for_location": {
        "uz": "📍 Jo‘nating manzilingizni (lokatsiya):",
        "ru": "📍 Отправьте своё местоположение:",
        "en": "📍 Please share your location:",
    },
    "order_placed_success": {
        "uz": "✅ Buyurtmangiz qabul qilindi! Tez orada operator bog‘lanadi.",
        "ru": "✅ Ваш заказ принят! Скоро с вами свяжется оператор.",
        "en": "✅ Your order has been placed! Our operator will contact you soon.",
    },
    "new_order_for_admin_tpl": {
        "uz": "🆕 Buyurtma #{daily_id} (ID: {id})\nMijoz: {customer_name}\nTelefon: {phone}\nSumma: {total} so'm",
        "ru": "🆕 Заказ #{daily_id} (ID: {id})\nКлиент: {customer_name}\nТелефон: {phone}\nСумма: {total} сум",
        "en": "🆕 Order #{daily_id} (ID: {id})\nCustomer: {customer_name}\nPhone: {phone}\nTotal: {total} so'm",
    },
    "ask_for_location_again": {
        "uz": "📍 Iltimos, lokatsiyani yuboring 👇",
        "ru": "📍 Пожалуйста, отправьте локацию 👇",
        "en": "📍 Please send your location 👇",
    },
    "orders_button": {"uz": "📦 Buyurtmalar", "ru": "📦 Заказы", "en": "📦 Orders"},
    "new_orders_list_title": {
        "uz": "📦 <b>Yangi buyurtmalar</b>:",
        "ru": "📦 <b>Новые заказы</b>:",
        "en": "📦 <b>New orders</b>:",
    },
    "no_new_orders": {"uz": "Yangi buyurtmalar yo‘q.", "ru": "Новых заказов нет.", "en": "No new orders."},
    "order_list_item_tpl": {
        "uz": "Buyurtma #{daily_id} — {total} so'm",
        "ru": "Заказ #{daily_id} — {total} сум",
        "en": "Order #{daily_id} — {total} so'm",
    },
    "ask_for_customer_name": {"uz": "Ismingizni kiriting:", "ru": "Введите ваше имя:", "en": "Enter your name:"},
    "order_details_tpl": {
        "uz": "<b>Buyurtma #{daily_id} (ID: {id})</b>\n{customer_label}: {name}\n{phone_label}: {phone}\n{items_label}:\n{items}\n{status_label}: {status}\n\n<b>Jami:</b> {total} so'm",
        "ru": "<b>Заказ #{daily_id} (ID: {id})</b>\n{customer_label}: {name}\n{phone_label}: {phone}\n{items_label}:\n{items}\n{status_label}: {status}\n\n<b>Итого:</b> {total} сум",
        "en": "<b>Order #{daily_id} (ID: {id})</b>\n{customer_label}: {name}\n{phone_label}: {phone}\n{items_label}:\n{items}\n{status_label}: {status}\n\n<b>Total:</b> {total} so'm",
    },
    "customer_label": {"uz": "Mijoz", "ru": "Клиент", "en": "Customer"},
    "phone_label": {"uz": "Telefon", "ru": "Телефон", "en": "Phone"},
    "items_label": {"uz": "Tovarlar", "ru": "Товары", "en": "Items"},
    "status_label": {"uz": "Holat", "ru": "Статус", "en": "Status"},
    "location_button": {"uz": "📍 Xarita", "ru": "📍 Карта", "en": "📍 Map"},
    "accept_order_button": {"uz": "✅ Qabul qilish", "ru": "✅ Принять", "en": "✅ Accept"},
    "order_accepted_alert": {"uz": "Buyurtma qabul qilindi!", "ru": "Заказ принят!", "en": "Order accepted!"},
    "order_status_updated_tpl": {
        "uz": "✅ Buyurtmangiz #{daily_id} qabul qilindi. Tez orada yetkazib beramiz!",
        "ru": "✅ Ваш заказ #{daily_id} принят! Скоро доставим.",
        "en": "✅ Your order #{daily_id} has been accepted and is being prepared!",
    },
    # ---------- Admin — Buyurtmalar paneli ----------
    "orders_dashboard_title": {
        "uz": "📊 Buyurtmalar paneli – holatni tanlang:",
        "ru": "📊 Панель заказов – выберите статус:",
        "en": "📊 Orders dashboard – choose status:",
    },
    "status_pending": {"uz": "🆕 Yangi", "ru": "🆕 Новые", "en": "🆕 Pending"},
    "status_processing": {"uz": "🔄 Jarayonda", "ru": "🔄 В процессе", "en": "🔄 Processing"},
    "status_delivered": {"uz": "✅ Yetkazildi", "ru": "✅ Доставлено", "en": "✅ Delivered"},
    "status_canceled": {"uz": "❌ Bekor qilingan", "ru": "❌ Отменённые", "en": "❌ Canceled"},
    "deliver_order_button": {"uz": "🚚 Yetkazib berishda", "ru": "🚚 В доставке", "en": "🚚 Out for delivery"},
    "complete_order_button": {"uz": "🏁 Yakunlash", "ru": "🏁 Завершить", "en": "🏁 Complete"},
    "order_status_delivering_tpl": {
        "uz": "🚚 Buyurtmangiz #{daily_id} yetkazib berish jarayonida.",
        "ru": "🚚 Ваш заказ #{daily_id} передан курьеру.",
        "en": "🚚 Your order #{daily_id} is out for delivery.",
    },
    "order_status_completed_tpl": {
        "uz": "🏁 Buyurtmangiz #{daily_id} yetkazildi. Yoqimli ishtaha!",
        "ru": "🏁 Ваш заказ #{daily_id} доставлен. Приятного аппетита!",
        "en": "🏁 Your order #{daily_id} has been delivered. Enjoy your meal!",
    },
    "delivering_orders_title": {
        "uz": "🚚 <b>Yetkazilayotgan buyurtmalar</b>:",
        "ru": "🚚 <b>Заказы в доставке</b>:",
        "en": "🚚 <b>Delivering orders</b>:",
    },
    "completed_orders_title": {
        "uz": "🏁 <b>Tugallangan buyurtmalar</b>:",
        "ru": "🏁 <b>Завершённые заказы</b>:",
        "en": "🏁 <b>Completed orders</b>:",
    },
    "canceled_orders_title": {
        "uz": "❌ <b>Bekor qilingan buyurtmalar</b>:",
        "ru": "❌ <b>Отменённые заказы</b>:",
        "en": "❌ <b>Canceled orders</b>:",
    },
    "processing_orders_title": {
        "uz": "🔄 <b>Jarayondagi buyurtmalar</b>:",
        "ru": "🔄 <b>Заказы в процессе</b>:",
        "en": "🔄 <b>Processing orders</b>:",
    },
    "delivered_orders_title": {
        "uz": "✅ <b>Yetkazilgan buyurtmalar</b>:",
        "ru": "✅ <b>Доставленные заказы</b>:",
        "en": "✅ <b>Delivered orders</b>:",
    },
    "order_delivering_alert": {
        "uz": "🚚 Buyurtma yetkazib berish jarayoniga o‘tildi!",
        "ru": "🚚 Заказ передан курьеру!",
        "en": "🚚 Order set to delivering!",
    },
    "order_completed_alert": {"uz": "🏁 Buyurtma yakunlandi!", "ru": "🏁 Заказ завершён!", "en": "🏁 Order completed!"},
    # --- Order status tugmalari ---
    "status_delivering": {"uz": "🚚 Yetkazishda", "ru": "🚚 В доставке", "en": "🚚 Delivering"},
    "status_completed": {"uz": "🏁 Tugallangan", "ru": "🏁 Завершённые", "en": "🏁 Completed"},
    "my_orders_button": {"uz": "👤 Buyurtmalarim", "ru": "👤 Мои заказы", "en": "👤 My orders"},
    "my_orders_list_title": {
        "uz": "👤 <b>Mening buyurtmalarim</b>:",
        "ru": "👤 <b>Мои заказы</b>:",
        "en": "👤 <b>My orders</b>:",
    },
    "no_orders_yet_history": {
        "uz": "Siz hali buyurtma qilmagansiz.",
        "ru": "Вы ещё не делали заказов.",
        "en": "You have no orders yet.",
    },
    "my_order_list_item_tpl": {
        "uz": "Buyurtma #{daily_id} — {total} so'm — {status}",
        "ru": "Заказ #{daily_id} — {total} сум — {status}",
        "en": "Order #{daily_id} — {total} so'm — {status}",
    },
    "cancel_order_button": {"uz": "❌ Bekor qilish", "ru": "❌ Отменить", "en": "❌ Cancel"},
    "confirm_cancel_prompt": {
        "uz": "⚠️ Buyurtma #{daily_id} ni bekor qilmoqchimisiz?",
        "ru": "⚠️ Отменить заказ #{daily_id}?",
        "en": "⚠️ Cancel order #{daily_id}?",
    },
    "order_canceled_alert": {"uz": "🗑 Buyurtma bekor qilindi!", "ru": "🗑 Заказ отменён!", "en": "🗑 Order canceled!"},
    "order_canceled_for_admin_tpl": {
        "uz": "❌ Buyurtma #{daily_id} (ID: {id}) mijoz tomonidan bekor qilindi.",
        "ru": "❌ Заказ #{daily_id} (ID: {id}) отменён клиентом.",
        "en": "❌ Order #{daily_id} (ID: {id}) was canceled by the customer.",
    },
    # --- Super Admin'ning bekor qilish oynasini sozlashga oid matnlar olib tashlandi ---
    # "sa_change_cancel_window_btn", "sa_prompt_new_cancel_window",
    # "invalid_cancel_window_error", "sa_cancel_window_updated" kalitlari olib tashlandi.
    # Bu sozlama endi .env faylidan olinadi.
    # --- Guruhni sozlashga oid keraksiz matnlar olib tashlandi ---
    # "set_group_command_info", "group_set_success" kalitlari olib tashlandi.
    # /set_group buyrug'i endi boshqacha ishlaydi.
    "not_a_group_error": {
        "uz": "❌ Bu buyruq faqat guruh chatida ishlaydi.",
        "ru": "❌ Эта команда работает только в групповых чатах.",
        "en": "❌ This command works only in group chats.",
    },
    "must_be_admin_error": {
        "uz": "❌ Sizda bu amalni bajarish uchun huquq yo'q.",
        "ru": "❌ У вас нет прав для выполнения этого действия.",
        "en": "❌ You do not have permission for this action.",
    },
    "claim_order_button": {"uz": "✋ Buyurtmani olish", "ru": "✋ Забрать заказ", "en": "✋ Claim order"},
    "manage_staff_button": {
        "uz": "🧑‍💼 Xodimlarni boshqarish",
        "ru": "🧑‍💼 Управление персоналом",
        "en": "🧑‍💼 Manage staff",
    },
    "staff_list_title": {
        "uz": "🧑‍💼 <b>Xodimlar ro‘yxati</b>:",
        "ru": "🧑‍💼 <b>Список персонала</b>:",
        "en": "🧑‍💼 <b>Staff list</b>:",
    },
    "add_staff_button": {"uz": "➕ Xodim qo‘shish", "ru": "➕ Добавить сотрудника", "en": "➕ Add staff"},
    "ask_for_staff_id": {
        "uz": "Iltimos, xodimning Telegram ID sini kiriting:",
        "ru": "Пожалуйста, введите Telegram ID сотрудника:",
        "en": "Please enter staff member’s Telegram ID:",
    },
    "staff_added_success": {
        "uz": "✅ Xodim muvaffaqiyatli qo‘shildi!",
        "ru": "✅ Сотрудник успешно добавлен!",
        "en": "✅ Staff member added successfully!",
    },
    "user_not_found_error": {
        "uz": "❌ Foydalanuvchi topilmadi. Iltimos, to‘g‘ri ID kiriting.",
        "ru": "❌ Пользователь не найден. Пожалуйста, введите корректный ID.",
        "en": "❌ User not found. Please enter a valid ID.",
    },
    "remove_staff_button": {"uz": "🗑 Xodimni ishdan boʻshatish", "ru": "🗑 Уволить сотрудника", "en": "🗑 Remove staff"},
    "confirm_staff_removal_tpl": {
        "uz": "⚠️ “{name}” (ID: {id}) xodimini ishdan boʻshatishga ishonchingiz komilmi?\nBu amal ortga qaytarib boʻlmaydi.",
        "ru": "⚠️ Вы уверены, что хотите уволить «{name}» (ID: {id})?\nЭто действие необратимо.",
        "en": "⚠️ Are you sure you want to remove “{name}” (ID: {id})?\nThis action cannot be undone.",
    },
    "staff_removed_success": {
        "uz": "✅ Xodim muvaffaqiyatli ishdan boʻshatildi.",
        "ru": "✅ Сотрудник успешно уволен.",
        "en": "✅ Staff member removed successfully.",
    },
    "edit_staff_name_button": {"uz": "✏️ Ismini o'zgartirish", "ru": "✏️ Изм. имя", "en": "✏️ Edit name"},
    "ask_for_staff_new_name": {
        "uz": "Iltimos, xodim #{id} uchun yangi ismni kiriting:",
        "ru": "Пожалуйста, введите новое имя для сотрудника #{id}:",
        "en": "Please enter a new name for staff #{id}:",
    },
    "staff_name_updated_success": {
        "uz": "✅ Xodimning ismi yangilandi!",
        "ru": "✅ Имя сотрудника обновлено!",
        "en": "✅ Staff name updated!",
    },
    "staff_panel_title": {
        "uz": "👨‍💼 Xodimlar paneli – amalni tanlang:",
        "ru": "👨‍💼 Панель сотрудников – выберите действие:",
        "en": "👨‍💼 Staff panel – choose an action:",
    },
    "order_already_claimed_by_tpl": {
        "uz": "❌ Bu buyurtma allaqachon {claimer_name} tomonidan olingan.",
        "ru": "❌ Этот заказ уже забрал {claimer_name}.",
        "en": "❌ This order was already claimed by {claimer_name}.",
    },
    "order_claimed_tpl": {
        "uz": '✅ Buyurtma #{daily_id} <a href="tg://user?id={claimer_id}">{claimer_name}</a> tomonidan qabul qilindi.',
        "ru": '✅ Заказ #{daily_id} забрал <a href="tg://user?id={claimer_id}">{claimer_name}</a>.',
        "en": '✅ Order #{daily_id} claimed by <a href="tg://user?id={claimer_id}">{claimer_name}</a>.',
    },
    "order_claimed_by_you_alert": {
        "uz": "✅ Buyurtma muvaffaqiyatli olindi!",
        "ru": "✅ Заказ успешно принят!",
        "en": "✅ Order successfully claimed!",
    },
    "order_was_canceled_alert": {
        "uz": "❌ Bu buyurtma mijoz tomonidan bekor qilingan.",
        "ru": "❌ Этот заказ был отменён клиентом.",
        "en": "❌ This order was canceled by the customer.",
    },
    "claimed_by_label": {"uz": "Qabul qilgan:", "ru": "Принял:", "en": "Accepted by:"},
    "manage_couriers_button": {
        "uz": "🏍 Kuriyerlarni boshqarish",
        "ru": "🏍 Управление курьерами",
        "en": "🏍 Manage Couriers",
    },
    "courier_list_title": {
        "uz": "🏍 <b>Kuriyerlar ro‘yxati</b>:",
        "ru": "🏍 <b>Список курьеров</b>:",
        "en": "🏍 <b>Couriers list</b>:",
    },
    "ask_for_courier_id": {
        "uz": "Iltimos, kuriyerning Telegram ID sini kiriting:",
        "ru": "Пожалуйста, введите Telegram ID курьера:",
        "en": "Please enter courier’s Telegram ID:",
    },
    "courier_added_success": {
        "uz": "✅ Kuriyer muvaffaqiyatli qo‘shildi!",
        "ru": "✅ Курьер успешно добавлен!",
        "en": "✅ Courier added successfully!",
    },
    "edit_courier_phone_button": {"uz": "☎️ Telefonni tahrirlash", "ru": "☎️ Изм. телефон", "en": "☎️ Edit phone"},
    "ask_for_courier_phone_tpl": {
        "uz": "Kuriyer #{id} telefon raqamini kiriting:",
        "ru": "Введите телефон курьера #{id}:",
        "en": "Enter phone number for courier #{id}:",
    },
    "courier_phone_updated": {
        "uz": "✅ Kuriyer telefon raqami yangilandi!",
        "ru": "✅ Телефон курьера обновлён!",
        "en": "✅ Courier phone number updated!",
    },
    "assign_to_courier_button": {
        "uz": "🚚 Kuriyerga tayinlash",
        "ru": "🚚 Назначить курьера",
        "en": "🚚 Assign to courier",
    },
    "choose_courier_title": {"uz": "🚚 Kuriyerni tanlang:", "ru": "🚚 Выберите курьера:", "en": "🚚 Choose a courier:"},
    "remove_courier_button": {"uz": "🗑 Kuriyerni o‘chirish", "ru": "🗑 Удалить курьера", "en": "🗑 Remove courier"},
    "confirm_courier_removal_tpl": {
        "uz": "⚠️ “{name}” (ID: {id}) kuriyerni o‘chirishga ishonchingiz komilmi?\nBu amal ortga qaytarib bo‘lmaydi.",
        "ru": "⚠️ Вы уверены, что хотите удалить курьера “{name}” (ID: {id})?\nЭто действие необратимо.",
        "en": "⚠️ Are you sure you want to remove courier “{name}” (ID: {id})?\nThis action cannot be undone.",
    },
    "courier_removed_success": {
        "uz": "✅ Kuriyer muvaffaqiyatli o‘chirildi!",
        "ru": "✅ Курьер успешно удалён!",
        "en": "✅ Courier removed successfully!",
    },
    "new_delivery_for_courier_tpl": {
        "uz": "🚚 Yangi yetkazib berish: buyurtma #{daily_id}.\nMijoz: {customer_name}\nTelefon: {customer_phone}",
        "ru": "🚚 Новая доставка: заказ #{daily_id}.\nКлиент: {customer_name}\nТелефон: {customer_phone}",
        "en": "🚚 New delivery: order #{daily_id}.\nCustomer: {customer_name}\nPhone: {customer_phone}",
    },
    "view_location_button": {"uz": "📍 Xaritani ko‘rish", "ru": "📍 Посмотреть на карте", "en": "📍 View on map"},
    "courier_confirm_delivery_button": {"uz": "✅ Yetkazildi", "ru": "✅ Доставлено", "en": "✅ I have delivered"},
    "order_assigned_to_courier_for_customer_tpl": {
        "uz": "✅ Buyurtma #{daily_id} muvaffaqiyatli kuryerga topshirildi!\n🚚 Kuryer: {courier_name}\n📞 Telefon: {courier_phone}\n🏁 Tez orada yetkaziladi.",
        "ru": "✅ Заказ #{daily_id} успешно передан курьеру!\n🚚 Курьер: {courier_name}\n📞 Телефон: {courier_phone}\n\n🏁 Скоро будет доставлено.",
        "en": "✅ Order #{daily_id} has been assigned to the courier!\n🚚 Courier: {courier_name}\n📞 Phone: {courier_phone}\n🏁 It will be delivered soon.",
    },
    "delivery_confirmed_alert_customer": {
        "uz": "✅ Yetkazib berish tasdiqlandi. Rahmat!",
        "ru": "✅ Доставка подтверждена. Спасибо!",
        "en": "✅ Delivery confirmed. Thank you!",
    },
    "delivery_issue_notification_admin_tpl": {
        "uz": "❗️ Mijoz buyurtma #{daily_id} ni qabul qilmadi.",
        "ru": "❗️ Клиент не подтвердил заказ #{daily_id}.",
        "en": "❗️ Customer did not confirm order #{daily_id}.",
    },
    "ask_customer_delivery_confirmation_tpl": {
        "uz": "Buyurtma #{daily_id} yetkazildimi?",
        "ru": "Заказ #{daily_id} доставлен?",
        "en": "Has order #{daily_id} been delivered?",
    },
    "customer_confirm_delivery_button": {"uz": "✅ Ha", "ru": "✅ Да", "en": "✅ Yes"},
    "customer_reject_delivery_button": {"uz": "❌ Yo‘q", "ru": "❌ Нет", "en": "❌ No"},
    "courier_delivery_requested": {
        "uz": "✅ Tasdiqlash mijozdan so‘ralmoqda…",
        "ru": "✅ Запрос подтверждения у клиента…",
        "en": "✅ Requesting confirmation from customer…",
    },
    "customer_delivery_thanks": {
        "uz": "✅ Yetkazib berish tasdiqlandi. Rahmat!",
        "ru": "✅ Доставка подтверждена. Спасибо!",
        "en": "✅ Delivery confirmed. Thank you!",
    },
    "order_completed_notification_tpl": {
        "uz": "Buyurtma #{daily_id} muvaffaqiyatli yakunlandi.",
        "ru": "Заказ #{daily_id} успешно завершён.",
        "en": "Order #{daily_id} has been successfully completed.",
    },
    "customer_dispute_info": {
        "uz": "❗ Muammo qayd etildi. Tez orada administrator siz bilan bog‘lanadi.",
        "ru": "❗ Проблема зафиксирована. Администратор свяжется с вами в ближайшее время.",
        "en": "❗ The issue has been reported. An admin will contact you shortly.",
    },
    "alert_order_rejected_tpl": {
        "uz": "❗️DIQQAT: Mijoz buyurtmani rad etdi! Buyurtma #{daily_id}",
        "ru": "❗️ВНИМАНИЕ: Клиент отклонил доставку! Заказ #{daily_id}",
        "en": "❗️ALERT: Customer has rejected the delivery! Order #{daily_id}",
    },
    "courier_delivery_completed": {
        "uz": "🏁 Yetkazish muvaffaqiyatli yakunlandi!",
        "ru": "🏁 Доставка успешно завершена!",
        "en": "🏁 Delivery successfully completed!",
    },
    "order_completed_tpl": {
        "uz": "🏁 Buyurtma #{daily_id} yakunlandi.",
        "ru": "🏁 Заказ #{daily_id} завершен.",
        "en": "🏁 Order #{daily_id} has been completed.",
    },
    "courier_panel_title": {
        "uz": "🏍 <b>Kuryer paneli</b>:",
        "ru": "🏍 <b>Панель курьера</b>:",
        "en": "🏍 <b>Courier Panel</b>:",
    },
    "my_active_deliveries_button": {
        "uz": "📦 Faol yetkazib berishlarim",
        "ru": "📦 Мои активные доставки",
        "en": "📦 My Active Deliveries",
    },
    "active_deliveries_list_title": {
        "uz": "📦 <b>Faol buyurtmalar</b>:",
        "ru": "📦 <b>Активные заказы</b>:",
        "en": "📦 <b>Active Deliveries</b>:",
    },
    "no_active_deliveries": {
        "uz": "Hozircha faol yetkazib berishlar yo‘q.",
        "ru": "Нет активных доставок.",
        "en": "No active deliveries yet.",
    },
    "status_disputed": {"uz": "❗️ Munozarali", "ru": "❗️ Спорные", "en": "❗️ Disputed"},
    "disputed_orders_title": {
        "uz": "❗️ <b>Munozarali buyurtmalar</b>:",
        "ru": "❗️ <b>Спорные заказы</b>:",
        "en": "❗️ <b>Disputed orders</b>:",
    },
    "no_disputed_orders": {
        "uz": "Munozarali buyurtmalar yo‘q.",
        "ru": "Спорных заказов нет.",
        "en": "No disputed orders.",
    },
    "manually_complete_button": {
        "uz": "✅ Qo‘lda yakunlash",
        "ru": "✅ Завершить вручную",
        "en": "✅ Manually Complete",
    },
    "cancel_disputed_button": {"uz": "❌ Buyurtmani bekor qilish", "ru": "❌ Отменить заказ", "en": "❌ Cancel Order"},
    "order_canceled_by_admin_tpl": {
        "uz": "❌ Sizning buyurtmangiz #{daily_id} administrator tomonidan bekor qilindi.",
        "ru": "❌ Ваш заказ #{daily_id} был отменён администратором.",
        "en": "❌ Your order #{daily_id} has been canceled by the admin.",
    },
    "manage_permissions_button": {
        "uz": "🔑 Huquqlarni boshqarish:",
        "ru": "🔑 Управление правами:",
        "en": "🔑 Manage permissions:",
    },
    "perm_manage_menu": {
        "uz": "Menyu boshqarish",
        "ru": "Управлять меню",
        "en": "Manage menu",
    },
    "perm_manage_orders": {
        "uz": "Buyurtmalarni boshqarish",
        "ru": "Управлять заказами",
        "en": "Manage orders",
    },
    "perm_manage_couriers": {
        "uz": "Kuriyerlarni boshqarish",
        "ru": "Управлять курьерами",
        "en": "Manage couriers",
    },
    "perm_admin_successor": {
        "uz": "To‘liq huquq (merosxo‘r)",
        "ru": "Полные права (наследник)",
        "en": "Full rights (successor)",
    },
    "perm_toggle_btn_tpl": {
        "uz": "{icon} {perm}",
        "ru": "{icon} {perm}",
        "en": "{icon} {perm}",
    },
    "perm_updated_alert": {
        "uz": "✅ Huquq yangilandi!",
        "ru": "✅ Право обновлено!",
        "en": "✅ Permission updated!",
    },
    "manage_staff_member_title_tpl": {
        "uz": "🧑‍💼 Xodim: {name}",
        "ru": "🧑‍💼 Сотрудник: {name}",
        "en": "🧑‍💼 Staff: {name}",
    },
    "staff_no_permissions_assigned": {
        "uz": "⚠️ Sizga hali hech qanday huquq berilmagan. Iltimos, administratoringiz bilan bog‘laning.",
        "ru": "⚠️ Вам ещё не назначены права. Пожалуйста, свяжитесь с администратором.",
        "en": "⚠️ You have not been granted any permissions yet. Please contact your administrator.",
    },
    "manage_courier_member_title_tpl": {"uz": "🏍 Kuriyer: {name}", "ru": "🏍 Курьер: {name}", "en": "🏍 Courier: {name}"},
    "team_management_button": {"uz": "👥 Jamoa boshqaruvi", "ru": "👥 Управление командой", "en": "👥 Team Management"},
    "settings_button": {"uz": "⚙️ Sozlamalar", "ru": "⚙️ Настройки", "en": "⚙️ Settings"},
    "team_management_title": {
        "uz": "👥 <b>Jamoa boshqaruvi</b>",
        "ru": "👥 <b>Управление командой</b>",
        "en": "👥 <b>Team Management</b>",
    },
    "settings_title": {"uz": "⚙️ <b>Sozlamalar</b>", "ru": "⚙️ <b>Настройки</b>", "en": "⚙️ <b>Settings</b>"},
    "subcategory_list_title": {
        "uz": "📂 <b>Ichki kategoriyalar</b>:",
        "ru": "📂 <b>Подкатегории</b>:",
        "en": "📂 <b>Sub-categories</b>:",
    },
    "product_list_title": {"uz": "🍔 <b>Mahsulotlar</b>:", "ru": "🍔 <b>Товары</b>:", "en": "🍔 <b>Products</b>:"},
    "manage_category_details_btn": {
        "uz": "⚙️ Kategoriya tafsilotlari",
        "ru": "⚙️ Параметры категории",
        "en": "⚙️ Category details",
    },
    "category_name_updated": {
        "uz": "✅ Kategoriya nomi yangilandi!",
        "ru": "✅ Название категории обновлено!",
        "en": "✅ Category name updated!",
    },
    "date_filter_title": {
        "uz": "🗓 <b>Sanani tanlang</b>:",
        "ru": "🗓 <b>Выберите дату</b>:",
        "en": "🗓 <b>Select a date</b>:",
    },
    "quick_select_button": {
        "uz": "🚀 Tez tanlash",
        "ru": "🚀 Быстрый выбор",
        "en": "🚀 Quick Select",
    },
    "specific_date_button": {
        "uz": "📅 Aniq sana",
        "ru": "📅 Конкретная дата",
        "en": "📅 Specific Date",
    },
    "quick_today_btn": {"uz": "Bugun", "ru": "Сегодня", "en": "Today"},
    "quick_week_btn": {"uz": "Bu hafta", "ru": "Эта неделя", "en": "This Week"},
    "quick_month_btn": {"uz": "Bu oy", "ru": "Этот месяц", "en": "This Month"},
    "date_range_tag_tpl": {
        "uz": "📅 {frm} → {to}",
        "ru": "📅 {frm} → {to}",
        "en": "📅 {frm} → {to}",
    },
    "no_orders_for_range": {
        "uz": "Tanlangan sanada buyurtmalar topilmadi.",
        "ru": "Заказы за выбранный период не найдены.",
        "en": "No orders for the selected period.",
    },
    "calendar_cancel_btn": {
        "uz": "Bekor qilish",
        "ru": "Отмена",
        "en": "Cancel",
    },
    "calendar_today_btn": {
        "uz": "Bugun",
        "ru": "Сегодня",
        "en": "Today",
    },
    # "manage_tags_btn" kaliti ko'p restoranli tizimga oid bo'lgani uchun olib tashlandi.
    "customer_main_menu_title": {
        "uz": "🏷 <b>Lazzatlar dunyosiga xush kelibsiz!</b>:",
        "ru": "🏷 <b>Добро пожаловать в мир вкусов!</b>:",
        "en": "🏷 <b>Welcome to the world of flavors!</b>:",
    },
    "lang_mismatch_warning": {
        "uz": "Ushbu restoran tilingizni qo‘llamasligi mumkin. Davom etasizmi?",
        "ru": "Этот ресторан может не поддерживать ваш язык. Продолжить?",
        "en": "This restaurant may not support your language. Continue?",
    },
    "confirm_continue": {"uz": "✅ Ha, davom etish", "ru": "✅ Да, продолжить", "en": "✅ Yes, continue"},
    "confirm_cancel": {"uz": "❌ Yo‘q", "ru": "❌ Нет", "en": "❌ No"},
    "manage_zone_btn": {"uz": "📍 Zonani boshqarish", "ru": "📍 Управление зоной", "en": "📍 Manage Zone"},
    "sa_manage_zone_tpl": {
        "uz": "📍 <b>{name}</b> uchun yetkazib berish zonasi boshqaruvi:",
        "ru": "📍 Управление зоной доставки для <b>{name}</b>:",
        "en": "📍 Delivery zone management for <b>{name}</b>:",
    },
    "change_zone_location_btn": {
        "uz": "🔄 Joylashuvni o'zgartirish",
        "ru": "🔄 Изменить местоположение",
        "en": "🔄 Change Location",
    },
    "change_zone_radius_btn": {"uz": "⭕️ Radiusni o'zgartirish", "ru": "⭕️ Изменить радиус", "en": "⭕️ Change Radius"},
    "sa_step4_enter_location": {
        "uz": "4️⃣ Iltimos, restoran joylashuvini lokatsiya orqali yuboring (yoki /cancel):",
        "ru": "4️⃣ Пожалуйста, отправьте местоположение ресторана (или /cancel):",
        "en": "4️⃣ Please send the restaurant location (or /cancel):",
    },
    "sa_step5_enter_radius": {
        "uz": "5️⃣ Yetkazib berish radiusini kilometrda kiriting (masalan: 5):",
        "ru": "5️⃣ Введите радиус доставки в километрах (например: 5):",
        "en": "5️⃣ Enter delivery radius in kilometers (e.g.: 5):",
    },
    "invalid_radius_error": {
        "uz": "❌ Radius musbat son bo‘lishi kerak. Qayta kiriting.",
        "ru": "❌ Радиус должен быть положительным числом. Попробуйте снова.",
        "en": "❌ Radius must be a positive number. Try again.",
    },
    "sa_zone_updated_location_tpl": {
        "uz": "✅ Zona joylashuvi yangilandi: lat={lat}, lon={lon}.",
        "ru": "✅ Местоположение зоны обновлено: lat={lat}, lon={lon}.",
        "en": "✅ Zone location updated: lat={lat}, lon={lon}.",
    },
    "sa_zone_updated_radius_tpl": {
        "uz": "✅ Zona radiusi yangilandi: {radius} km.",
        "ru": "✅ Радиус зоны обновлен: {radius} км.",
        "en": "✅ Zone radius updated: {radius} km.",
    },
    "no_restaurants_delivery_area": {
        "uz": "Afsuski, hozirgi joylashuvingiz uchun yetkazib berish zonalari mavjud emas.",
        "ru": "К сожалению, в вашей зоне доставки нет ресторанов.",
        "en": "Sorry, no restaurants deliver to your area.",
    },
    "reenter_location_button": {
        "uz": "🔄 Lokatsiyani qaytadan yuborish",
        "ru": "🔄 Отправить местоположение заново",
        "en": "🔄 Re-enter location",
    },
    "address_confirmation_tpl": {
        "uz": "📍 Sizning manzilingiz: <b>{address}</b>\nTo‘g‘rimi?",
        "ru": "📍 Ваш адрес: <b>{address}</b>\nПравильно?",
        "en": "📍 Your address is: <b>{address}</b>\nCorrect?",
    },
    "confirm_address_yes": {"uz": "✅ To‘g‘ri", "ru": "✅ Верно", "en": "✅ Yes"},
    "reenter_location": {"uz": "🔄 Yana yuborish", "ru": "🔄 Отправить заново", "en": "🔄 Send New Location"},
    "my_addresses_button": {"uz": "📍 Mening manzillarim", "ru": "📍 Мои адреса", "en": "📍 My Addresses"},
    # Manzillar ro‘yxati sahifasi
    "address_list_title": {
        "uz": "📍 <b>Mening manzillarim</b>:",
        "ru": "📍 <b>Мои адреса</b>:",
        "en": "📍 <b>My Addresses</b>:",
    },
    "no_saved_addresses": {
        "uz": "Sizda saqlangan manzillar yo‘q.",
        "ru": "У вас пока нет сохранённых адресов.",
        "en": "You have no saved addresses.",
    },
    # Manzillarni boshqarish tugmalari
    "add_new_address_button": {
        "uz": "➕ Yangi manzil qo‘shish",
        "ru": "➕ Добавить новый адрес",
        "en": "➕ Add New Address",
    },
    "delete_address_button": {"uz": "🗑 O‘chirish", "ru": "🗑 Удалить", "en": "🗑 Delete"},
    # FSM so‘rovlari
    "ask_for_address_location": {
        "uz": "📍 Iltimos, yangi manzilingizni lokatsiya orqali yuboring:",
        "ru": "📍 Пожалуйста, отправьте местоположение нового адреса:",
        "en": "📍 Please send the location for your new address:",
    },
    "ask_for_address_name": {
        "uz": "📝 Iltimos, ushbu manzilga nom bering (masalan, Uy, Ish):",
        "ru": "📝 Пожалуйста, дайте имя этому адресу (например, Дом, Работа):",
        "en": "📝 Please name this address (e.g., Home, Work):",
    },
    "address_saved_success": {"uz": "✅ Manzil saqlandi!", "ru": "✅ Адрес сохранён!", "en": "✅ Address saved!"},
    "address_deleted_success": {"uz": "✅ Manzil o‘chirildi!", "ru": "✅ Адрес удалён!", "en": "✅ Address deleted!"},
    "address_not_found": {"uz": "Manzil topilmadi", "ru": "Адрес не найден", "en": "Address not found"},
    "language_settings_button": {"uz": "⚙️ Til sozlamalari", "ru": "⚙️ Языковые настройки", "en": "⚙️ Language Settings"},
    "language_management_title": {
        "uz": "Botda ishlatiladigan tillarni boshqaring:",
        "ru": "Управление языками, используемыми в боте:",
        "en": "Manage languages used in the bot:",
    },
    "reset_daily_id_button": {
        "uz": "🔄 Kundalik ID ni yangilash",
        "ru": "🔄 Сбросить дневной ID",
        "en": "🔄 Reset Daily ID",
    },
    "confirm_reset_prompt": {
        "uz": "⚠️ Haqiqatan ham kundalik buyurtma hisoblagichini yangilamoqchimisiz? Keyingi buyurtma raqami 1 dan boshlanadi.",
        "ru": "⚠️ Вы уверены, что хотите сбросить счетчик заказов? Следующий заказ получит номер 1.",
        "en": "⚠️ Are you sure you want to reset the daily order counter? The next order will be number 1.",
    },
    "reset_success_alert": {
        "uz": "✅ Hisoblagich muvaffaqiyatli yangilandi!",
        "ru": "✅ Счетчик успешно сброшен!",
        "en": "✅ Counter has been reset successfully!",
    },
    "set_location_btn": {
        "uz": "🔄 Joylashuvni o‘zgartirish",
        "ru": "🔄 Изменить местоположение",
        "en": "🔄 Change Location",
    },
    "set_radius_btn": {"uz": "⭕️ Radiusni o‘zgartirish", "ru": "⭕️ Изменить радиус", "en": "⭕️ Change Radius"},
    "current_zone_info_tpl": {
        "uz": "📍 <b>Joriy zona:</b>\nLat: {lat}\nLon: {lon}\nRadius: {radius} km",
        "ru": "📍 <b>Текущая зона:</b>\nШирота: {lat}\nДолгота: {lon}\nРадиус: {radius} км",
        "en": "📍 <b>Current zone:</b>\nLat: {lat}\nLon: {lon}\nRadius: {radius} km",
    },
    "ask_for_cafe_location": {
        "uz": "📍 Iltimos, restoran joylashuvini lokatsiya orqali yuboring:",
        "ru": "📍 Пожалуйста, отправьте местоположение ресторана:",
        "en": "📍 Please send the restaurant location:",
    },
    "ask_for_radius_km": {
        "uz": "⭕️ Radiusni kilometrda kiriting (masalan: 5):",
        "ru": "⭕️ Введите радиус в километрах (например: 5):",
        "en": "⭕️ Enter radius in kilometers (e.g.: 5):",
    },
    "location_updated_success": {
        "uz": "✅ Zona joylashuvi yangilandi!",
        "ru": "✅ Местоположение зоны обновлено!",
        "en": "✅ Zone location updated!",
    },
    "radius_updated_success": {
        "uz": "✅ Zona radiusi yangilandi!",
        "ru": "✅ Радиус зоны обновлен!",
        "en": "✅ Zone radius updated!",
    },
    "add_courier_btn": {"uz": "➕ Kuriyer qo‘shish", "ru": "➕ Добавить курьера", "en": "➕ Add Courier"},
    "user_is_already_courier": {
        "uz": "❌ Bu foydalanuvchi allaqachon kuriyer!",
        "ru": "❌ Этот пользователь уже курьер!",
        "en": "❌ This user is already a courier!",
    },
    "ask_for_courier_name": {
        "uz": "Kuriyerning to‘liq ismini kiriting:",
        "ru": "Введите полное имя курьера:",
        "en": "Enter the courier’s full name:",
    },
    "ask_for_courier_phone": {
        "uz": "Kuriyer telefon raqamini kiriting yoki /skip yuboring:",
        "ru": "Введите телефон курьера или отправьте /skip:",
        "en": "Enter the courier’s phone number or send /skip:",
    },
    "assign_to_courier_btn": {
        "uz": "🚚 Kuriyerga tayinlash",
        "ru": "🚚 Назначить курьера",
        "en": "🚚 Assign to courier",
    },
    "no_available_couriers_alert": {
        "uz": "❌ Mavjud kuryerlar yo‘q.",
        "ru": "❌ Нет доступных курьеров.",
        "en": "❌ No available couriers.",
    },
    "courier_assigned_success_alert": {
        "uz": "✅ Kuryer muvaffaqiyatli tayinlandi!",
        "ru": "✅ Курьер успешно назначен!",
        "en": "✅ Courier assigned successfully!",
    },
    "courier_delivery_requested_alert": {
        "uz": "✅ Tasdiqlash mijozdan so‘ralmoqda…",
        "ru": "✅ Запрос подтверждения у клиента…",
        "en": "✅ Requesting confirmation from customer…",
    },
    "view_order_details_btn": {
        "uz": "Buyurtma tafsilotlarini ko‘rish",
        "ru": "Просмотр деталей заказа",
        "en": "View order details",
    },
    "delivery_success_for_courier": {
        "uz": "✅ Mijoz yetkazishni tasdiqladi!",
        "ru": "✅ Клиент подтвердил доставку!",
        "en": "✅ Customer confirmed the delivery!",
    },
    "delivery_failed_for_courier": {
        "uz": "❌ Mijoz yetkazishni tasdiqlamadi. Administrator bilan bog‘laning.",
        "ru": "❌ Клиент не подтвердил доставку. Свяжитесь с администратором.",
        "en": "❌ Customer did not confirm the delivery. Please contact admin.",
    },
    "active_delivery_item_tpl": {
        "uz": "Buyurtma #{daily_id} — Mijoz: {customer_name}",
        "ru": "Заказ #{daily_id} — Клиент: {customer_name}",
        "en": "Order #{daily_id} — Customer: {customer_name}",
    },
    "remove_courier_btn": {"uz": "🗑 Kuriyerni o‘chirish", "ru": "🗑 Удалить курьера", "en": "🗑 Remove courier"},
    "user_is_already_active_courier": {
        "uz": "❌ Bu foydalanuvchi allaqachon faol kuriyer!",
        "ru": "❌ Этот пользователь уже является активным курьером!",
        "en": "❌ This user is already an active courier!",
    },
    "confirm_courier_reactivation_tpl": {
        "uz": "Kuriyer «{name}» qayta faollashtirilsinmi?",
        "ru": "Активировать курьера «{name}» снова?",
        "en": "Reactivate courier “{name}”?",
    },
    "courier_reactivated_success": {
        "uz": "✅ Kuriyer muvaffaqiyatli qayta faollashtirildi!",
        "ru": "✅ Курьер успешно реактивирован!",
        "en": "✅ Courier has been successfully reactivated!",
    },
    "assigned_courier_info_tpl": {
        "uz": "🚚 Kuryer: {courier_name}",
        "ru": "🚚 Курьер: {courier_name}",
        "en": "🚚 Courier: {courier_name}",
    },
    "set_cancel_window_btn": {
        "uz": "⏱️ Bekor qilish oynasini o'rnatish",
        "ru": "⏱️ Установить окно отмены",
        "en": "⏱️ Set cancel window",
    },
    "ask_for_cancel_window": {
        "uz": "Joriy qiymat: {current_minutes} daqiqa. Yangisini kiriting:",
        "ru": "Текущее значение: {current_minutes} минут. Введите новое:",
        "en": "Current value: {current_minutes} minutes. Please enter a new one:",
    },
    "cancel_window_updated_success": {
        "uz": "Bekor qilish oynasi yangilandi!",
        "ru": "Окно отмены обновлено!",
        "en": "Cancel window updated successfully!",
    },
    "invalid_minutes_error": {
        "uz": "Iltimos, musbat butun son kiriting.",
        "ru": "Пожалуйста, введите положительное целое число.",
        "en": "Please enter a positive integer.",
    },
    "set_work_hours_btn": {
        "uz": "🕒 Ish vaqtini belgilash",
        "ru": "🕒 Установить рабочее время",
        "en": "🕒 Set working hours",
    },
    "ask_for_start_time_tpl": {
        "uz": "Hozirgi ish vaqti: {start} - {end}.\nYangi ochilish vaqtini (HH:MM) kiriting:",
        "ru": "Текущее время работы: {start} - {end}.\nВведите новое время открытия (HH:MM):",
        "en": "Current hours: {start} - {end}.\nPlease enter new opening time (HH:MM):",
    },
    "ask_for_end_time": {
        "uz": "Yopilish vaqtini (HH:MM) kiriting:",
        "ru": "Введите время закрытия (HH:MM):",
        "en": "Please enter closing time (HH:MM):",
    },
    "invalid_time_format_error": {
        "uz": "Xato format. Iltimos, vaqtni HH:MM formatida kiriting.",
        "ru": "Неверный формат. Введите время в формате HH:MM.",
        "en": "Invalid format. Please use HH:MM.",
    },
    "work_hours_updated_success": {
        "uz": "✅ Ish vaqti muvaffaqiyatli yangilandi!",
        "ru": "✅ Рабочее время успешно обновлено!",
        "en": "✅ Working hours updated successfully!",
    },
    "not_set_label": {"uz": "Belgilanmagan", "ru": "Не задано", "en": "Not set"},
    "cafe_is_closed_tpl": {
        "uz": "Kechirasiz, biz {start_time} dan {end_time} gacha ishlaymiz.",
        "ru": "Извините, мы работаем с {start_time} до {end_time}.",
        "en": "Sorry, we operate from {start_time} to {end_time}.",
    },
    # Bufer vaqti tugmasi
    "set_order_buffer_btn": {
        "uz": "🔧 Bufer vaqtini oʻrnatish",
        "ru": "🔧 Установить буфер",
        "en": "🔧 Set Order Buffer",
    },
    # Hozirgi bufer qiymatini ko‘rsatib, yangisini kiritishni so‘rash
    "ask_for_order_buffer_tpl": {
        "uz": "Hozirgi bufer: {current_buffer} daqiqa. Yangisini kiriting:",
        "ru": "Текущий буфер: {current_buffer} минут. Введите новое значение:",
        "en": "Current buffer: {current_buffer} minutes. Please enter new value:",
    },
    # Muvaffaqiyatli yangilanish xabari
    "order_buffer_updated_success": {
        "uz": "✅ Bufer vaqti yangilandi!",
        "ru": "✅ Буферное время обновлено!",
        "en": "✅ Order buffer time updated!",
    },
    "make_unavailable_btn": {"uz": "🚫 Sotuvdan olish", "ru": "🚫 Снять с продажи", "en": "🚫 Remove from sale"},
    "make_available_btn": {"uz": "✅ Sotuvga qaytarish", "ru": "✅ Вернуть в продажу", "en": "✅ Return to sale"},
    "daily_report_btn": {"uz": "📊 Kunlik Hisobot", "ru": "📊 Ежедневный отчет", "en": "📊 Daily Report"},
    "no_best_seller_label": {"uz": "Mavjud emas", "ru": "Нет данных", "en": "N/A"},
    "daily_report_tpl": {
        "uz": (
            "📊 Bugungi hisobot:\n\n"
            "- Yakunlangan buyurtmalar: {count} ta\n"
            "- Umumiy summa: {total_sum} so'm\n"
            "- Eng ko'p sotilgan mahsulot: {best_seller}"
        ),
        "ru": (
            "📊 Ежедневный отчет:\n\n"
            "- Завершенные заказы: {count} шт\n"
            "- Общая сумма: {total_sum} сум\n"
            "- Самый продаваемый товар: {best_seller}"
        ),
        "en": (
            "📊 Daily Report:\n\n"
            "- Completed orders: {count}\n"
            "- Total amount: {total_sum}\n"
            "- Best-selling product: {best_seller}"
        ),
    },
    "manage_variations_btn": {
        "uz": "⚙️ Variantlarni boshqarish",
        "ru": "⚙️ Управление вариантами",
        "en": "⚙️ Manage Variations",
    },
    "variation_list_title": {
        "uz": "📋 Mahsulot variantlari ro‘yxati:",
        "ru": "📋 Список вариантов товара:",
        "en": "📋 Product Variations List:",
    },
    "add_variation_btn": {"uz": "➕ Yangi variant qo‘shish", "ru": "➕ Добавить вариант", "en": "➕ Add New Variation"},
    "no_variations_yet": {
        "uz": "Hozircha variantlar qo‘shilmagan.",
        "ru": "Пока нет вариантов.",
        "en": "No variations yet.",
    },
    "ask_for_variation_name_tpl": {
        "uz": "{lang} tilida variant nomini kiriting (masalan, Katta, Pishloqli):",
        "ru": "Введите название варианта на языке {lang} (например, Большой, Сырный):",
        "en": "Enter the variation name in {lang} (e.g. Large, Cheese):",
    },
    "ask_for_variation_price": {
        "uz": "Ushbu variant uchun to‘liq narxni kiriting:",
        "ru": "Введите окончательную цену для этого варианта:",
        "en": "Please enter the full price for this variation:",
    },
    "variation_added_success": {
        "uz": "✅ Variant muvaffaqiyatli qo‘shildi!",
        "ru": "✅ Вариант успешно добавлен!",
        "en": "✅ Variation added successfully!",
    },
    "ask_for_variation_photo": {
        "uz": "📸 Variant uchun alohida rasm yuboring. Yoki Umumiy mahsulot rasmini ishlatish uchun /skip buyrug‘ini yuboring.",
        "ru": "📸 Отправьте уникальное фото варианта. Чтобы использовать фото основного товара, отправьте /skip.",
        "en": "📸 Please send a unique photo for this variation. To use the parent product's photo instead, send /skip.",
    },
    "ask_for_new_variation_price": {
        "uz": "Yangi narxni kiriting:",
        "ru": "Введите новую цену варианта:",
        "en": "Enter new variation price:",
    },
    "variation_price_updated": {
        "uz": "✅ Variant narxi yangilandi!",
        "ru": "✅ Цена варианта обновлена!",
        "en": "✅ Variation price updated!",
    },
    "ask_for_new_variation_name_tpl": {
        "uz": "{lang} tilida variant uchun yangi nom kiriting:",
        "ru": "Введите новое имя варианта на языке {lang}:",
        "en": "Enter new variation name in {lang}:",
    },
    "variation_name_updated": {
        "uz": "✅ Variant nomi yangilandi!",
        "ru": "✅ Название варианта обновлено!",
        "en": "✅ Variation name updated!",
    },
    "ask_for_new_variation_photo": {
        "uz": "Variant uchun yangi rasm yuboring yoki joriy rasmni o'chirish uchun /remove deb yozing.",
        "ru": "Отправьте новое фото варианта или введите /remove, чтобы удалить текущее фото.",
        "en": "Send a new variation photo or type /remove to delete the current photo.",
    },
    "variation_photo_updated": {
        "uz": "✅ Variant rasmi yangilandi!",
        "ru": "✅ Фото варианта обновлено!",
        "en": "✅ Variation photo updated!",
    },
    "add_N_to_cart_btn": {"uz": "📥 Savatga qo'shish", "ru": "📥 В корзину", "en": "📥 Add to cart"},
    "confirm_variation_delete_tpl": {
        "uz": "⚠️ “{name}” variantini o‘chirishga ishonchingiz komilmi?",
        "ru": "⚠️ Удалить вариант «{name}»?",
        "en": "⚠️ Delete variation “{name}”?",
    },
    "variation_deleted_success": {
        "uz": "🗑 Variant muvaffaqiyatli o‘chirildi!",
        "ru": "🗑 Вариант успешно удалён!",
        "en": "🗑 Variation deleted successfully!",
    },
    # ---------- 2.0: kodda ishlatilgan, lekin lug'atda yo'q bo'lgan kalitlar ----------
    "category_not_found": {
        "uz": "Kategoriya topilmadi.",
        "ru": "Категория не найдена.",
        "en": "Category not found.",
    },
    "no_enabled_languages_error": {
        "uz": "Hech qanday til yoqilmagan. Avval Sozlamalar → Tillar bo‘limida kamida bitta tilni yoqing.",
        "ru": "Нет включённых языков. Сначала включите хотя бы один язык в Настройки → Языки.",
        "en": "No languages are enabled. Enable at least one in Settings → Languages first.",
    },
    # ---------- 2.0: xavfsizlik va holat tekshiruvlari ----------
    "access_denied_alert": {
        "uz": "⛔ Bu amal siz uchun mavjud emas.",
        "ru": "⛔ Это действие вам недоступно.",
        "en": "⛔ This action is not available to you.",
    },
    "order_not_found_alert": {"uz": "Buyurtma topilmadi.", "ru": "Заказ не найден.", "en": "Order not found."},
    "order_status_conflict_alert": {
        "uz": "⚠️ Buyurtma holati allaqachon o‘zgargan. Ro‘yxatni yangilang.",
        "ru": "⚠️ Статус заказа уже изменился. Обновите список.",
        "en": "⚠️ The order status has already changed. Please refresh.",
    },
    "unable_to_cancel_alert": {
        "uz": "Buyurtmani endi bekor qilib bo‘lmaydi.",
        "ru": "Этот заказ уже нельзя отменить.",
        "en": "This order can no longer be canceled.",
    },
    "order_location_out_of_zone": {
        "uz": "Afsuski, bu manzil yetkazib berish hududidan tashqarida. Iltimos, boshqa lokatsiya yuboring.",
        "ru": "К сожалению, этот адрес вне зоны доставки. Пожалуйста, отправьте другую геолокацию.",
        "en": "Sorry, this address is outside our delivery area. Please send another location.",
    },
}
