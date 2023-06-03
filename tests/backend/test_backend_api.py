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
def test_user_register(client, user_factory):
    user = user_factory()
    response = client.post(f'http://{host}:8000/api/v1/user/register',
                           {'email': user.email, 'password': user.password})
    token_email = ConfirmEmailToken.objects.get(user_id=user.id)
    print(token_email.key)
    assert response.status_code == HTTP_200_OK



@pytest.mark.django_db
def test_user_login(client, user_factory):
    user = user_factory()
    response = client.post(f'http://{host}:8000/api/v1/user/login',  {'email': user.email, 'password': user.password})
    assert response.status_code == 200


@pytest.mark.django_db
def test_contact_anonymous_get(client):
    factory = APIRequestFactory()
    request = factory.get(f'http://{host}:8000/api/v1/user/contact')
    view = ContactViewSet.as_view(actions={'get': 'retrieve'})
    response = view(request)
    assert response.status_code == 403


@pytest.mark.django_db
def test_contact_create(client, contact_factory, user_factory):
    user = user_factory()
    user.is_active = True
    response = client.post(f'http://{host}:8000/api/v1/user/login', {'email': user.email, 'password': user.password})
    assert response.status_code == 200
    email_token = ConfirmEmailToken.objects.get(user_id=user.id)
    print(email_token.key, 'email_token.key')
    token = baker.make('authtoken.Token', user__id=user.id)
    contact = baker.make('backend.Contact', user__id=user.id)
    factory = APIRequestFactory()

    request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                           {'user_id': contact.user_id, 'city': contact.city,
                            'street': contact.street, 'phone': contact.phone}, HTTP_AUTHORIZATION='Token ' + token.key)

    view = ContactViewSet.as_view(actions={'post': 'create'})
    response = view(request)
    assert response.status_code == 200