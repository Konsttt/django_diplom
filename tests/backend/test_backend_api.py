import pytest
from rest_framework.authtoken.models import Token
from rest_framework.status import HTTP_200_OK
from rest_framework.test import APIRequestFactory, force_authenticate
import os
from backend.models import Contact, Shop, Category, ProductInfo, Product, Order, OrderItem
from backend.views import ContactViewSet

host = os.getenv('SERVER_HOST')


# {
#     'get': 'retrieve',
#     'post': 'create',
#     'put': 'update',
#     'patch': 'partial_update',
#     'delete': 'destroy'
# }

# создание пользователя (регистрация)
@pytest.mark.django_db
def test_user_register(client, user_factory):
    user = user_factory()
    response = client.post(f'http://{host}:8000/api/v1/user/register',
                           {'email': user.email, 'password': user.password})
    assert response.status_code == HTTP_200_OK


# логин - вход по почте и паролю
@pytest.mark.django_db
def test_user_login(client, user_factory):
    user = user_factory()
    response = client.post(f'http://{host}:8000/api/v1/user/login',  {'email': user.email, 'password': user.password})
    assert response.status_code == 200


# login/logout - выход пользователя
@pytest.mark.django_db
def test_user_logout(client, user_factory):
    user = user_factory()
    user.is_active = True
    Token.objects.create(user=user)
    client.post(f'http://{host}:8000/api/v1/user/login', {'email': user.email, 'password': user.password})
    client.force_authenticate(user=user, token=user.auth_token)
    response = client.get(f'http://{host}:8000/api/v1/user/logout')
    assert response.status_code == 200
    data = response.json()
    assert data.get('Status')  # True
    assert data.get('email') == user.email


# у анонима нет доступа к просмотру контактов
@pytest.mark.django_db
def test_contact_anonymous_get(client):
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


# Создание 1-го контакта и просмотр своего контакта авторизованным пользователем
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
    citys_2 = []  # соберём список городов, чтобы потом сверить с response
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
    # Так как вывод в view.py сортируется по городам (для лучшей пагинации), то сверяем город по отсортированному списку
    for i in range(5):
        assert data.get('results')[i].get('city') == sorted(citys_2)[i]


# Менеджер магазина загружает в БД товары из yaml-файла. Проверяем, товары в БД,
# по заранее известным названиям из yaml-файла.
# yaml-файл загружается по url и лежит в папке /media,
# поэтому для успешного тестирования, чтобы файл был доступен - нужно запустить проект - runserver
@pytest.mark.django_db
def test_partner_update_products(client, user_factory):
    # создаём менеджера
    user = user_factory()
    user.is_active = True
    user.type = 'shop'
    Token.objects.create(user=user)
    # авторизуемся
    client.force_authenticate(user=user, token=user.auth_token)
    # get-запрос (проверка, что открывается template-форма загрузки файла)
    response = client.get(f'http://{host}:8000/api/v1/partner/update')
    assert response.status_code == 200
    # загрузка данных по товарам в БД из yaml-файла, url должен быть рабочий
    response = client.post(f'http://{host}:8000/api/v1/partner/update',
                           {'url': 'http://localhost:8000/api/v1/media/files/ozon.yaml'})
    assert response.status_code == 200
    response = client.get(f'http://{host}:8000/api/v1/shops')
    assert response.status_code == 200
    # data = response.json()
    # print(data)  # !!! вывод в консоль для дебага с опцией: pytest -s   # без -s не всегда печатает
    # В файле .yaml название магазина было Ozone, категорий - Смартфоны и т.д. Они и записались в таблицы БД
    assert 'Ozon' in [shop.name for shop in Shop.objects.all()]
    assert 'Смартфоны' in [category.name for category in Category.objects.all()]
    assert 'xiaomi/redmi/13 pro' in [model.model for model in ProductInfo.objects.all()]


# Любой пользователь видит магазины
@pytest.mark.django_db
def test_get_shops(client):
    response = client.get(f'http://{host}:8000/api/v1/shops')
    assert response.status_code == 200


# Любой пользователь видит категории
@pytest.mark.django_db
def test_get_shops(client):
    response = client.get(f'http://{host}:8000/api/v1/categories')
    assert response.status_code == 200


# Любой пользователь видит информацию о товарах
@pytest.mark.django_db
def test_get_shops(client):
    response = client.get(f'http://{host}:8000/api/v1/products')
    assert response.status_code == 200


# Просмотр своей корзины
@pytest.mark.django_db
def test_get_basket(client, user_factory):
    # создаём пользователя
    user = user_factory()
    user.is_active = True
    Token.objects.create(user=user)
    # авторизуемся
    client.force_authenticate(user=user, token=user.auth_token)
    # get-запрос
    response = client.get(f'http://{host}:8000/api/v1/basket')
    assert response.status_code == 200


# Наполняем корзину и оформляем заказ
@pytest.mark.django_db
def test_post_basket(client, user_factory, contact_factory):
    # Подготовка данных. Заполнение всех таблиц с товарами
    # создаём менеджера
    user_m = user_factory()
    user_m.is_active = True
    user_m.type = 'shop'
    Token.objects.create(user=user_m)
    # авторизуемся
    client.force_authenticate(user=user_m, token=user_m.auth_token)
    # Создаём магазин
    shop = Shop.objects.create(user_id=user_m.id, name='Ozon', state=True)
    # Создаём категорию
    category = Category.objects.create(name='Смартфоны')
    # Создаём продукт
    product = Product.objects.create(name='Xiaomi 13 pro 256Гб', category=category)
    # Создаём информацию о продукте
    product_info = ProductInfo.objects.create(model='xiaomi 13 pro', external_id=23423423, quantity=1000,
                                              price=70000, price_rrc=75000, product=product, shop=shop)
    # разлогиниваемся менеджером
    client.get(f'http://{host}:8000/api/v1/user/logout')

    # создаём пользователя, который наполняет себе корзину
    user = user_factory()
    user.is_active = True
    Token.objects.create(user=user)
    # авторизуемся
    client.force_authenticate(user=user, token=user.auth_token)
    # post-запрос - положили товар в корзину
    response = client.post(f'http://{host}:8000/api/v1/basket',
                           {'items': '[{\"product_info\": ' + str(product_info.id) + ', \"quantity\": 10}]'})
    assert response.status_code == 200
    assert OrderItem.objects.get(product_info_id=product_info.id).quantity == 10
    assert Order.objects.get(user_id=user.id).user_id == user.id
    assert Order.objects.get(user_id=user.id).state == 'basket'
    # теперь нужно создать контакт (для оформления заказа)
    contact = contact_factory()
    factory = APIRequestFactory()
    request = factory.post(f'http://{host}:8000/api/v1/user/contact',
                           {'user': user.id, 'city': contact.city,
                            'street': contact.street, 'phone': contact.phone})
    force_authenticate(request, user=user, token=user.auth_token)
    view = ContactViewSet.as_view(actions={'post': 'create'})
    response = view(request)
    assert response.status_code == 201
    # из корзины оформляем заказ
    client.force_authenticate(user=user, token=user.auth_token)
    response = client.post(f'http://{host}:8000/api/v1/order',
                           {'id': str(Order.objects.get(user_id=user.id).id),
                            'contact': Contact.objects.get(user_id=user.id).id})
    assert response.status_code == 200
    assert Order.objects.get(user_id=user.id).state == 'new'  # Заказ оформлен (basket поменялся на new)


# Просмотр своих заказов
@pytest.mark.django_db
def test_get_order(client, user_factory):
    # создаём пользователя
    user = user_factory()
    user.is_active = True
    Token.objects.create(user=user)
    # авторизуемся
    client.force_authenticate(user=user, token=user.auth_token)
    # get-запрос
    response = client.get(f'http://{host}:8000/api/v1/order')
    assert response.status_code == 200


# Тест на троттлинг. Аноним обновляет 10 раз страницу с товарами.
@pytest.mark.django_db
def test_throttle_get_products(client):
    # Цикл 9 раз, т.к. выше уже есть 1 такой запрос (Итого 10 запросов отрабатывает).
    for _ in range(9):
        # get-запрос в лимите троттлинга
        response = client.get(f'http://{host}:8000/api/v1/products')
        assert response.status_code == 200
    # На 11 запросе отрабатывает ограничение по троттлингу
    response = client.get(f'http://{host}:8000/api/v1/products')
    assert response.status_code == 429  # HTTP 429 Too Many Requests


