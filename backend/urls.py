from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from backend.views import PartnerUpdate, RegisterAccount, LoginAccount, CategoryView, ShopView, ProductInfoView, \
    BasketView, AccountDetails, ContactView, OrderView, PartnerState, PartnerOrders, ConfirmAccount, LogoutAccount, \
    UploadFilesView

from django.conf import settings
from django.conf.urls.static import static


app_name = 'backend'
urlpatterns = [
    # Загрузка локального файла с товарами менеджером на сервер
    path('partner/upload_file/', UploadFilesView.as_view(), name="upload_files"),
    # Загрузка товаров/магазинов в БД данных из файла
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    # Просмотр/изменение_статуса своих магазинов менеджером
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    # Просмотр оформленных заказов поставщиками, каждый видит заказанные товары только из своего магазина
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    # Первоначальная регистрация
    # (пользователь ещё не активирован, пользователю отправляется письмо со ссылкой на активацию)
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    # Подтверждение почты (переход по ссылке в письме), активация пользователя
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    # Просмотр и редактирование своих данных пользователем
    path('user/details', AccountDetails.as_view(), name='user-details'),
    # CRUD своих адресов
    path('user/contact', ContactView.as_view(), name='user-contact'),
    # Вход по логину и паролю активированного пользователя, создаётся токен, если его нет.
    path('user/login', LoginAccount.as_view(), name='user-login'),
    # Выход пользователя - удаление токена.
    path('user/logout', LogoutAccount.as_view(), name='user-logout'),
    # Запрос на сброс пароля. На почту приходит временный токен.
    path('user/password_reset', reset_password_request_token, name='password-reset'),
    # Сброс пароля (новый пароль + временный токен из почты)
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),
    # Просмотр всех категорий товаров любым пользователем
    path('categories', CategoryView.as_view(), name='categories'),
    # Просмотр всех магазинов любым пользователем
    path('shops', ShopView.as_view(), name='shops'),
    # Поиск товаров по магазину и/или категории товара
    path('products', ProductInfoView.as_view(), name='shops'),
    # Наполнение корзины, удаление товара из корзины, изменения кол-ва выбранных товаров в корзине
    path('basket', BasketView.as_view(), name='basket'),
    # Оформление из корзины нового заказа. Просмотр всех своих заказов.
    path('order', OrderView.as_view(), name='order'),
    # Файлы .yaml с товарами магазинов загружаются и хранятся в папке /media/files/
    # В БД в таблице uploadfiles хранится владелец файла, путь к файлу, название файла
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
