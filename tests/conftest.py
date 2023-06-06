import pytest
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from model_bakery import baker

from backend.models import User, Contact
from django.contrib.auth.models import auth
from django.core.management import call_command


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def user_factory():
    def factory(*args, **kwargs):
        return baker.make(User, *args, **kwargs)
    return factory


@pytest.fixture
def contact_factory(user_factory):
    def factory(*args, **kwargs):
        return baker.make('backend.Contact', user=user_factory())
    return factory



