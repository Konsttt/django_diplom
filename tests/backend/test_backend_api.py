import pytest
from model_bakery import baker
from rest_framework.authtoken.models import Token
from rest_framework.status import HTTP_200_OK
from rest_framework.test import APIRequestFactory, force_authenticate
import os
from django.urls import reverse
from backend.models import ConfirmEmailToken, Contact, User
from backend.views import ContactViewSet


host = os.getenv('SERVER_HOST')


# {
#     'get': 'retrieve',
#     'post': 'create',
#     'put': 'update',
#     'patch': 'partial_update',
#     'delete': 'destroy'
# }

@pytest.mark.django_db
def test_user_register(client, user_factory):  # регистрация пользователя
    user = user_factory()
    response = client.post(f'http://{host}:8000/api/v1/user/register',
                           {'email': user.email, 'password': user.password})
    assert response.status_code == HTTP_200_OK



@pytest.mark.django_db
def test_user_login(client, user_factory):  # логин - вход по почте и паролю
    user = user_factory()
    response = client.post(f'http://{host}:8000/api/v1/user/login',  {'email': user.email, 'password': user.password})
    assert response.status_code == 200


@pytest.mark.django_db
def test_contact_anonymous_get(client):  # пресечение попытки доступа к контактам для анонима
    factory = APIRequestFactory()
    request = factory.get(f'http://{host}:8000/api/v1/user/contact')
    view = ContactViewSet.as_view(actions={'get': 'retrieve'})
    response = view(request)
    assert response.status_code == 403


# Создание своего контакта авторизованным по токену пользователем.
@pytest.mark.django_db
def test_contact_create(client, user_factory, contact_factory):
    user = user_factory()
    user.is_active = True
    Token.objects.create(user=user)
    contact = contact_factory()
    factory = APIRequestFactory()
    request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                           {'user': user.id, 'city': contact.city,
                            'street': contact.street, 'phone': contact.phone})
    force_authenticate(request, user=user, token=user.auth_token)
    view = ContactViewSet.as_view(actions={'post': 'create'})
    response = view(request)
    assert response.status_code == 201


# Неудачная попытка создания контакта не авторизованным пользователем.
@pytest.mark.django_db
def test_contact_anonim_create(client, user_factory, contact_factory):
    user = user_factory()
    user.is_active = True
    contact = contact_factory()
    factory = APIRequestFactory()
    request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                           {'user': user.id, 'city': contact.city,
                            'street': contact.street, 'phone': contact.phone})
    view = ContactViewSet.as_view(actions={'post': 'create'})
    response = view(request)
    assert response.status_code == 403


# Создание и просмотр своих контактов авторизованным пользователем
@pytest.mark.django_db
def test_get_my_contact(client, user_factory, contact_factory):
    user = user_factory()
    user.is_active = True
    Token.objects.create(user=user)
    contact = contact_factory()
    factory = APIRequestFactory()
    request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                           {'user': user.id, 'city': contact.city,
                            'street': contact.street, 'phone': contact.phone})
    force_authenticate(request, user=user, token=user.auth_token)
    view = ContactViewSet.as_view(actions={'post': 'create'})
    response = view(request)
    assert response.status_code == 201
    request2 = factory.get(f'http://{host}:8000/api/v1/user/contact')
    force_authenticate(request2, user=user, token=user.auth_token)
    view2 = ContactViewSet.as_view(actions={'get': 'list'})  # !!! не retriev  !!! (тест крашился)
    response = view2(request2)
    assert response.status_code == 200


# Просмотр всех контактов менеджером магазина
@pytest.mark.django_db
def test_get_all_contact(client, user_factory, contact_factory):
    factory = APIRequestFactory()
    # создаём 1 пользователя
    user1 = user_factory()
    user1.is_active = True
    Token.objects.create(user=user1)
    # создаём 2 пользователя
    user2 = user_factory()
    user2.is_active = True
    Token.objects.create(user=user2)
    # создаём по 5 контактов у каждого пользователя
    for user in [user1, user2]:
        for _ in range(5):
            contact = contact_factory()
            request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                                   {'user': user.id, 'city': contact.city,
                                    'street': contact.street, 'phone': contact.phone})
            force_authenticate(request, user=user, token=user.auth_token)
            ContactViewSet.as_view(actions={'post': 'create'})
    # создаём менеджера
    user_m = user_factory()
    user_m.is_active = True
    user_m.type = 'shop'
    Token.objects.create(user=user_m)
    # Менеджер просматривает все контакты
    request2 = factory.get(f'http://{host}:8000/api/v1/user/contact')
    force_authenticate(request2, user=user_m, token=user_m.auth_token)
    view2 = ContactViewSet.as_view(actions={'get': 'list'})
    response = view2(request2)
    data = response.data
    assert response.status_code == 200
    assert data.get('count') == 10  # менеджер просматривает 10 контактов

# Просмотр только своих контактов пользователем
@pytest.mark.django_db
def test_get_own_contact(client, user_factory, contact_factory):
    factory = APIRequestFactory()
    # создаём 1 пользователя
    user1 = user_factory()
    user1.is_active = True
    Token.objects.create(user=user1)
    # создаём 5 контактов 1 пользователя
    for _ in range(5):
        contact = contact_factory()
        request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                               {'user': user1.id, 'city': contact.city,
                                'street': contact.street, 'phone': contact.phone})
        force_authenticate(request, user=user1, token=user1.auth_token)
        view = ContactViewSet.as_view(actions={'post': 'create'})
        view(request)
    # создаём 2 пользователя
    user2 = user_factory()
    user2.is_active = True
    Token.objects.create(user=user2)
    # создаём 5 контактов 2 пользователя
    citys_2 = []
    for _ in range(5):
        contact = contact_factory()
        request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                               {'user': user2.id, 'city': contact.city,
                                'street': contact.street, 'phone': contact.phone})
        citys_2.append(contact.city)
        force_authenticate(request, user=user2, token=user2.auth_token)
        view = ContactViewSet.as_view(actions={'post': 'create'})
        view(request)
    # запрос списка контактов 2-м пользователем
    request = factory.get(f'http://{host}:8000/api/v1/user/contact')
    force_authenticate(request, user=user2, token=user2.auth_token)
    view = ContactViewSet.as_view(actions={'get': 'list'})
    response = view(request)
    data = response.data
    assert response.status_code == 200
    assert data.get('count') == 5  # user2 видит только свои 5 контактов
    # Так как вывод для лучшей пагинации сортируется по городам, то сверяем город по отсортированному списку
    assert data.get('results')[3].get('city') == sorted(citys_2)[3]