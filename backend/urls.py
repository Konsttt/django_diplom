from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from backend.views import PartnerUpdate, RegisterAccount, LoginAccount, CategoryView, ShopView, ProductInfoView, \
    BasketView, AccountDetails, ContactView, OrderView, PartnerState, PartnerOrders, ConfirmAccount, LogoutAccount, \
    UploadFilesView

from django.conf import settings
from django.conf.urls.static import static


app_name = 'backend'
urlpatterns = [
    path('partner/upload_file/', UploadFilesView.as_view(), name="upload_files"),
    path('partner/update', PartnerUpdate.as_view(), name='partner-update'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/orders', PartnerOrders.as_view(), name='partner-orders'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),  # Первоначальная регистрация (пользователь ещё не активирован)
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),  # Подтверждение почты, активация пользователя
    path('user/details', AccountDetails.as_view(), name='user-details'),  # Просмотр и редактирование своих данных
    path('user/contact', ContactView.as_view(), name='user-contact'),  # CRUD своих адресов
    path('user/login', LoginAccount.as_view(), name='user-login'),  # Вход по логину и паролю активированного пользователя, создаётся токен, если его нет.
    path('user/logout', LogoutAccount.as_view(), name='user-logout'),  # Выход пользователя - удаление токена.
    path('user/password_reset', reset_password_request_token, name='password-reset'),  # запрос на сброс пароля. на почту приходит временный токен.
    path('user/password_reset/confirm', reset_password_confirm, name='password-reset-confirm'),  # сброс пароля (новый пароль + временный токен из почты)
    path('categories', CategoryView.as_view(), name='categories'),
    path('shops', ShopView.as_view(), name='shops'),
    path('products', ProductInfoView.as_view(), name='shops'),
    path('basket', BasketView.as_view(), name='basket'),
    path('order', OrderView.as_view(), name='order'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

