from django.urls import path
from rest_framework.routers import DefaultRouter

from backend.views import PartnerUpdate, RegisterAccount, LoginAccount, CategoryView, ShopView, ProductInfoView, \
    BasketView, AccountDetails, OrderView, PartnerOrders, ConfirmAccount, LogoutAccount, \
    UploadFilesView, ResetPassword, EnterNewPassword, ContactViewSet, PartnerShopSet, PartnerCategorySet, \
    PartnerProductSet

from django.conf import settings
from django.conf.urls.static import static

r = DefaultRouter()
# Просмотр и редактирование пользователями своих контактов, пользователи видят только свои контакты,
# у менеджеров только просмотр всех контактов, без возможности редактирования, у админа все права
r.register('user/contact', ContactViewSet, basename='user-contact')  # Для ссылок user-contact-list
# У менеджеров просмотр и редактирование только своих магазинов, у админа все права
# У пользователей и анонимов только просмотр всех магазинов по url 'shops' см. ниже
r.register('partner/shop', PartnerShopSet, basename='partner-shop')
# Редактирование менеджерами названий своих товаров, админ редактирует все товары.
# Методы post и patch - для всех запрещены, т.к. есть связанные сущности по id,
# (post: товары штатно добавляются из файла по url partner/update), разрешены только get, put и delete.
# У пользователей и анонимов здесь запрет на всё. Пользователи и анонимы смотрят товары по адресу - /products)
r.register('partner/product', PartnerProductSet, basename='partner-product-info')

app_name = 'backend'  # !!! теперь в url в templates нужно указывать {% url 'backend:shops'%} !!!
urlpatterns = [
    # Загрузка локального файла с товарами менеджером на сервер
    path('partner/upload_file/', UploadFilesView.as_view(), name="upload_files"),
    # Загрузка товаров/магазинов в БД данных из файла
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    # Просмотр оформленных заказов поставщиками, каждый видит заказанные товары только из своего магазина
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    # Первоначальная регистрация
    # (пользователь ещё не активирован, пользователю отправляется письмо со ссылкой на активацию)
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    # Подтверждение почты (переход по ссылке в письме), активация пользователя
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    # Просмотр и редактирование своих данных пользователем
    path('user/details', AccountDetails.as_view(), name='user-details'),
    # Вход по логину и паролю активированного пользователя, создаётся токен, если его нет.
    path('user/login', LoginAccount.as_view(), name='user-login'),
    # Выход пользователя - удаление токена.
    path('user/logout', LogoutAccount.as_view(), name='user-logout'),
    # Запрос на сброс пароля. На почту приходит временный токен.
    path('user/password_reset', ResetPassword.as_view(), name='password-reset'),  # reset_password_request_token
    # Сброс пароля (новый пароль + временный токен из почты)
    path('user/password_reset/confirm', EnterNewPassword.as_view(), name='password-reset-confirm'),
    # Просмотр всех категорий товаров любым пользователем
    path('categories', CategoryView.as_view(), name='categories'),
    # Просмотр всех магазинов любым пользователем
    path('shops', ShopView.as_view(), name='shops'),
    # Поиск товаров по магазину и/или категории товара
    path('products', ProductInfoView.as_view(), name='products'),
    # Наполнение корзины, удаление товара из корзины, изменения кол-ва выбранных товаров в корзине
    path('basket', BasketView.as_view(), name='basket'),
    # Оформление из корзины нового заказа. Просмотр всех своих заказов.
    path('order', OrderView.as_view(), name='order'),
    # Файлы .yaml с товарами магазинов загружаются и хранятся в папке /media/files/
    # В БД в таблице uploadfiles хранится владелец файла, путь к файлу, название файла
] + r.urls + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
