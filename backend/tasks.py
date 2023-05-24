# backend/tasks.py
import time
from time import sleep
from django.core.mail import EmailMultiAlternatives
from backend.models import ConfirmEmailToken
from django.conf import settings
from celery import shared_task


@shared_task()
def new_user_registered_mail_task(user_id, **kwargs):
    """
    Отправляем письмо с подтверждением аккаунта на почту пользователя.
    (По переходу по ссылке в письме пользователь активируется)
    """
    sleep(30)
    # send an e-mail to the user
    token, _ = ConfirmEmailToken.objects.get_or_create(user_id=user_id)

    msg = EmailMultiAlternatives(
        # title:
        f"Password Reset Token for {token.user.email}",
        # message:  # Ссылка для подтверждения аккаунта пользователя (https://localhost:8000  - заменить на свой домен)
        f"http://172.27.66.91:8000/api/v1/user/register/confirm?token={token.key}&email={token.user.email}",
        # from:
        settings.EMAIL_HOST_USER,
        # to:
        [token.user.email]
    )
    msg.send()