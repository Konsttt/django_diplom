# backend/tasks.py
from time import sleep
from django.core.mail import EmailMultiAlternatives

from backend.models import ConfirmEmailToken
from django.conf import settings
from celery import shared_task
from backend.models import User
import os


host = os.getenv('SERVER_HOST')


@shared_task()
def new_user_registered_mail_task(user_id, **kwargs):
    """
    Отправляем письмо с подтверждением аккаунта на почту пользователя.
    (По переходу по ссылке в письме пользователь активируется)
    """
    sleep(10)
    # send an e-mail to the user
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Password Reset Token for {token.user.email}",
        # message:
        f"http://{host}:8000/api/v1/user/register/confirm?token={token.key}&email={token.user.email}",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [token.user.email]
    )
    msg.send()


@shared_task()
def password_reset_token_mail_task(token, email, first_name, last_name):
    """
    Отправляем письмо с токеном для сброса пароля
    (По переходу по ссылке в письме пользователь попадает на страничку ввода нового пароля)
    """
    # send an e-mail to the user

    msg = EmailMultiAlternatives(
        # title:
        f"Password Reset Token for {first_name} {last_name}",
        # message:
        f"http://{host}:8000/api/v1/user/password_reset/confirm?token={token}",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [email]
    )
    msg.send()


@shared_task()
def new_order_mail_task(user_id, order_sum, order_id, **kwargs):
    """
    отправяем письмо при изменении статуса заказа
    (На почту приходит подтверждение оформленного заказа с номером заказа и общей суммой.)
    """
    # send an e-mail to the user
    user = User.objects.get(id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Обновление статуса заказа",
        # message:
        f'Заказ на сумму {order_sum} сформирован. Номер вашего заказа №{order_id}.',
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [user.email]
    )
    msg.send()
