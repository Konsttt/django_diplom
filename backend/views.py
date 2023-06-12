import datetime
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django_rest_passwordreset.views import ResetPasswordRequestToken, ResetPasswordConfirm
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_view, extend_schema, OpenApiParameter
from requests import get
from rest_framework.authtoken.models import Token
from django_rest_passwordreset.models import ResetPasswordToken
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from ujson import loads as load_json
from yaml import load as load_yaml, Loader
from backend.forms import UploadFilesForm, LoginForm, RegisterForm, ResetPasswordForm, EnterNewPasswordForm
from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, User, UploadFiles
from backend.permissions import IsOwnerAdminOrReadOnly, IsOwnerOrAdmin
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer, ProductSerializer, LoginSerializer
from backend.tasks import new_user_registered_mail_task, password_reset_token_mail_task, host, new_order_mail_task
from time import sleep


#  region api_documentation
@extend_schema(tags=["Регистрация пользователя, подтверждение регистрации"])
@extend_schema_view(
    get=extend_schema(
        summary="Открытие формы регистрации:  для ввода логина(email), пароля и других полей регистрации",
    ),
    post=extend_schema(
        summary="Регистрация:  отправка данных, результат - запись в БД логина(email), пароля и др. полей, "
                "отправка письма со ссылкой для подтверждения",
        description="В результате данного запроса пользователь записывается в БД, но не активирован. "
                    "Не сможет залогиниться пока не пройдёт по ссылке в письме. "
                    "Пройдя по ссылке - пользователь активируется, создаётся его постоянный токен."
                    "Теперь пользователь может логиниться.  "
                    "Чтобы пользователя перевести в статус менеджера - таких запросов в целях безопасности нет, "
                    "это может сделать только админ, через свою админку.",
        request=UserSerializer,
    ),
)
#  endregion
class RegisterAccount(APIView):
    """
    Регистрация пользователей.
    """
    throttle_classes = [UserRateThrottle]

    # Регистрация методом POST
    def post(self, request, *args, **kwargs):
        # проверяем обязательные аргументы
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):
            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                # проверяем данные для уникальности имени пользователя
                # request.data._mutable = True
                # request.data.update({})
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    # ! Вновь создаваемый пользователь, кроме пользователей авторизующихся через социальные сети,
                    # всегда не активирован! Активация происходит по ссылке на email - в методе 'user-register-confirm'
                    user.is_active = False
                    user.set_password(request.data['password'])
                    user.save()
                    new_user_registered_mail_task.delay(user_id=user.id)
                    return render(request, 'backend/success_reg.html')
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def get(self, request):
        form = RegisterForm()
        return render(request, 'backend/register.html', {'form': form})


#  region api_documentation
@extend_schema(tags=["Регистрация пользователя, подтверждение регистрации"],
               parameters=[
                   OpenApiParameter("email", OpenApiTypes.STR, OpenApiParameter.QUERY),
                   # serializer object is converted to a parameter
                   OpenApiParameter("token", OpenApiTypes.STR, OpenApiParameter.QUERY,
                                    description='Кроме почты токен можно взять из таблицы '
                                                'backend_confirmemailtoken'),
               ],
               )
@extend_schema_view(
    get=extend_schema(
        summary="Подтверждение регистрации: клик по ссылке в письме пользователя.",
    ),
)
#  endregion
class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    (После регистрации пользователя на почту пользователя приходит ссылка с токеном,
    по клику на ссылку отправляется запрос post с параметрами.
    По запросу post из таблицы confirmmailtoken - токен удаляется, а в таблицу authtoken_token - токен записывается,
    и пользователь активируется. Теперь при авторизации(login) будет использоваться токен из authtoken_token.)
    """

    # Подтверждение методом get с параметрами - по клику по ссылке в письме.
    def get(self, request):

        email_ = request.GET.get('email')
        token_ = request.GET.get('token')
        token = ConfirmEmailToken.objects.filter(user__email=email_, key=token_).first()
        if token:
            token.user.is_active = True
            token.user.save()
            auth_token = Token(user_id=token.user.id)  # key=token.key - это убрал, чтобы генерировался новый токен!
            auth_token.save()
            token.delete()
            return render(request, 'backend/register_confirm.html',
                          {'first_name': token.user.first_name, 'last_name': token.user.last_name})
        else:
            return JsonResponse({'Status': False, 'Errors': 'Неправильно указан токен или email'})


class AccountDetails(APIView):
    """
    Класс для работы с данными пользователя
    """

    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    # получить данные пользователя
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом POST
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # проверяем обязательные аргументы
        if 'password' in request.data:
            # errors = {}
            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


#  region api_documentation
@extend_schema(tags=["Login/Logout"])
@extend_schema_view(
    get=extend_schema(
        summary="Открытие формы для ввода логина(email) и пароля",
        description="Если пользователь уже аутентифицирован и повторно хочет открыть форму ввода логина и пароля, "
                    "то ему открывается сразу страница приветствия."
    ),
    post=extend_schema(
        summary="Ввод логина(email) и пароля, вход в систему",
        request=LoginSerializer,
    ),
)
#  endregion
class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    # Авторизация методом POST
    def post(self, request, *args, **kwargs):
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])
            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)
                    user.last_login = datetime.datetime.now()
                    user.save()
                    login(request, user)  # Вот теперь сохраняется сессия (токен в браузере) !!!
                    return render(request, 'backend/success_login.html',
                                  {'first_name': user.first_name, 'last_name': user.last_name})
            return JsonResponse({'Status': False, 'Errors': 'Wrong password'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    def get(self, request):
        # Если пользователь уже аутентифицирован и повторно логиниться, то открываем начальную страницу
        if request.user.is_authenticated:
            return render(request, 'backend/success_login.html',
                          {'first_name': request.user.first_name, 'last_name': request.user.last_name})
        form = LoginForm()
        return render(request, 'backend/login.html', {'form': form})


#  region api_documentation
@extend_schema(tags=["Login/Logout"])
@extend_schema_view(
    get=extend_schema(
        summary="Выход пользователя из системы",
    )
)
#  endregion
class LogoutAccount(APIView):
    """
    Выход пользователя
    """

    def get(self, request):
        # token = request.auth.pk
        # token_db = Token.objects.get(key=token)
        # if token_db:
        #     logout_user_id = token_db.user_id
        #     logout_user_email = User.objects.get(id=logout_user_id).email
        #     logout(request)
        if request.user.is_authenticated:
            logout_user_email = request.user.email
            logout(request)  # Очистка сессии на клиенте (браузере) !!!
            return JsonResponse({'Status': True, 'email': logout_user_email, 'Message': 'You are logout'})
        return JsonResponse({'Status': False, 'Message': 'Your are already logout'})


# Для редиректа с джанговского url 'accounts/profile/',
# куда по умолчанию осуществляется переход после подтверждения данных авторизации из VK,
# на свою страничку с логином
def redirect_login_view(request):
    response = redirect('backend:user-login')
    return response



#  region api_documentation
@extend_schema(tags=["Категории товаров"])
@extend_schema_view(
    get=extend_schema(
        summary="Вывод всех категорий товаров",
    )
)
#  endregion
# по умолчанию только get метод, если в классе не определён ни один метод
class CategoryView(ListAPIView):
    """
    Класс для просмотра всех категорий любым пользователем/анонимом
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

#  region api_documentation
@extend_schema(tags=["Категории товаров"])
@extend_schema_view(
    get=extend_schema(
        summary="Вывод менеджером только своих Категорий",
    )
)
#  endregion
class PartnerCategorySet(ModelViewSet):
    """
    Класс для редактирования своих Категорий товаров менеджерами или любой категории админом.
    Менеджер магазина видит только свои Категории.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsOwnerAdminOrReadOnly]

    # Переопределение метода, чтобы менеджер магазина видел только свои магазины, а админ все.
    def get_queryset(self):
        queryset = Category.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)
        return queryset


# по умолчанию только get метод
class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer
    throttle_classes = [AnonRateThrottle, UserRateThrottle]


class ProductInfoView(APIView):
    """
    Класс для поиска товаров по магазину и/или категории товаров
    """
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    def get(self, request, *args, **kwargs):

        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отбрасываем дубликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)


class PartnerProductSet(ModelViewSet):
    """
    Класс для редактирования своих продуктов менеджерами
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
    # Т.к. запись связанная, то только редактирование. Запрет методов post и patch.
    http_method_names = ['get', 'put', 'head', 'delete']

    # Переопределение метода, чтобы менеджер магазина видел только свои продукты, а админ все.
    def get_queryset(self):
        queryset = Product.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(product_infos__shop__user=self.request.user.id)
        return queryset


#  region api_documentation
@extend_schema(tags=["Работа с Корзиной, оформление заказа"])
@extend_schema_view(
    get=extend_schema(
        summary="Просмотр своей корзины",
        parameters=[
            OpenApiParameter(
                name='Token',
                location=OpenApiParameter.PATH,
                description='Token',
                required=True,
                type=str,
            ),
        ],
    ),
    post=extend_schema(
        summary="Наполнение корзины товарами / создание корзины / добавление товара в козину",
    ),
    delete=extend_schema(
        summary="Удаление товаров из корзины",
    ),
    put=extend_schema(
        summary="Изменение кол-ва товара/товаров в корзине",
    ),
)
#  endregion
class BasketView(APIView):
    """
    Класс для работы с корзиной пользователя.
    Работа с таблицами:
     Order - корзина пользователя 'basket'/заказ 'new'
     OrderView товары из корзины/заказа пользователя
    """

    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    # получить корзину
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # Создать корзину (добавить в корзину товары)
    # Перед добавлением в корзину первого товара - создаётся корзина пользователя - одна запись в таблице Order (basket)
    # А так же в OrderItem - запись с выбранным товаром, id-корзины из Order(куда его положили), и кол-во товаров
    # Параметры запроса: product_info - id из таблицы productinfo и quantity - кол-во товаров
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Errors': str(error)})
                        else:
                            objects_created += 1

                    else:

                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # изменить позиции в корзине
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView):
    """
    Класс для обновления прайса от поставщика
    """

    # Форма с выпадающим списком всех загруженных файлов менеджера магазина.
    def get(self, request):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # ! Проверка, что аутентифицированный пользователь - менеджер магазина
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        files = UploadFiles.objects.filter(user_id=request.user.id)

        url = f'http://{host}:8000/api/v1/media/'
        names = [url + str(file.file) for file in files]

        return render(request, 'backend/choice_file.html', {'names': names})

    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # ! Проверка, что аутентифицированный пользователь - менеджер магазина
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return render(request, 'backend/success_products_update.html')

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerShopSet(ModelViewSet):
    queryset = Shop.objects.all()
    serializer_class = ShopSerializer
    permission_classes = [IsAuthenticated, IsOwnerAdminOrReadOnly]

    # Переопределение метода, чтобы менеджер магазина видел только свои магазины, а админ все.
    def get_queryset(self):
        queryset = Shop.objects.all()
        if not self.request.user.is_staff:
            queryset = queryset.filter(user_id=self.request.user.id)
        return queryset


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
    """

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactViewSet(ModelViewSet):
    queryset = Contact.objects.all()
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated, IsOwnerAdminOrReadOnly]
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    # Переопределение метода, чтобы пользователи видели только свои контакты, а админ и менеджеры магазина все.
    def get_queryset(self):
        queryset = Contact.objects.all().order_by('user_id')
        if not (self.request.user.is_staff or self.request.user.type == 'shop'):
            queryset = queryset.filter(user_id=self.request.user.id).order_by('city')
        return queryset


#  region api_documentation
@extend_schema(tags=["Работа с Корзиной, оформление Заказа"])
@extend_schema_view(
    get=extend_schema(
        summary="Просмотр всех своих оформленных Заказов",
    ),
    post=extend_schema(
        summary="Создать Заказ из Корзины. Статус заказа меняется с basket на new. "
                "Заказчику отправляется письмо-подтверждение.",
        description="Оформление заказа из корзины: "
                    "(в json запросе передаются id-корзины и id-адреса_доставки_пользователя, "
                    "т.к. корзин и контактво может быть у пользователя несколько) "
                    "У заказа статус меняется на new, на почту пользователю отправляется письмо - что заказ оформлен. "
                    "(Небольшой нюанс: id корзины передаётся строкой, id контакта - числом.)",
        request=OrderSerializer,
    ),
)
#  endregion
class OrderView(APIView):
    """
    Класс для создания из Корзины Заказа и просмотра своих Заказов.
    """

    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    # просмотр всех своих заказов (оформленных, не корзины)
    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)

    # Оформление заказа из корзины. Статус заказа меняется с basket на new. Заказчику отправляется письмо-подтверждение.
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=int(request.data['id'])).update(
                        contact_id=request.data['contact'],
                        state='new')
                except IntegrityError as error:
                    print(error)
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                else:
                    if is_updated:
                        # Формируем общую сумму нового заказа (по id-заказа и id-пользователя)
                        order = Order.objects.filter(
                            user_id=request.user.id, id=int(request.data['id'])).prefetch_related(
                            'ordered_items__product_info__product__category',
                            'ordered_items__product_info__product_parameters__parameter').select_related(
                            'contact').annotate(
                            total_sum=Sum(
                                F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
                        serializer = OrderSerializer(order, many=True)
                        order_sum = serializer.data[0]['total_sum']
                        # Отправка письма о новом заказе с помощью Celery
                        new_order_mail_task.delay(request.user.id, order_sum, request.data['id'])
                        return render(request, 'backend/success_new_order.html',
                                      {'id': request.data['id'], 'order_sum': order_sum})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class UploadFilesView(APIView):
    """
   Загрузка файлов с товарами с локального компьютера в БД через форму в браузере.
   """

    def post(self, request, *args, **kwargs):
        # Проверка по токену
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # Проверка, что аутентифицированный пользователь - менеджер магазина
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        form = UploadFilesForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
        return render(request, 'backend/success_upload_file.html')

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        # Проверка, что аутентифицированный пользователь - менеджер магазина
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        # ! Автоматическое заполнение скрытых полей формы - user (id) и email: initial !
        form = UploadFilesForm(initial={'user': self.request.user.id, 'email': self.request.user.email})
        # В результате get-запроса отображается форма с двумя полями ввода - имя файла и загрузка файла,
        # и кнопка Загрузить.
        return render(request, 'backend/upload.html', {'form': form})


class ResetPassword(ResetPasswordRequestToken):
    """
    Класс для сброса пароля
    """
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    # Переопределение метода post родительского класса ради Celery
    def post(self, request, *args, **kwargs):
        status = super(ResetPassword, self).post(request)
        if status.status_code == 200:  # Родительская функция отработала хорошо (и могла бы отправить сигнал-письмо)
            # Все проверки прошли в родительской форме.
            email = request.data['email']
            user = User.objects.get(email=email)
            token = ResetPasswordToken.objects.get(user_id=user.id).key
            # Отправка письма с данными для сброса пароля с помощью функционала Celery
            password_reset_token_mail_task.delay(token, email, user.first_name, user.last_name)
            return render(request, 'backend/success_reset_psw.html')
        return status

    # Форма для ввода почты (для любого пользователя)
    def get(self, request):
        form = ResetPasswordForm()
        return render(request, 'backend/password_reset.html', {'form': form})


class EnterNewPassword(ResetPasswordConfirm):
    throttle_classes = [AnonRateThrottle, UserRateThrottle]

    # Форма для ввода почты
    def get(self, request):
        email = self.request.query_params.get('email')
        token = self.request.query_params.get('token')

        # Если запрос без параметров (т.е. напрямую, а не по ссылке из письма), то выбрасывает на страничку с логином
        if not token or not email:
            return render(request, 'backend/bad_token.html')

        user = User.objects.filter(email=email).first()
        # Если в базе нет такого пользователя
        if not user:
            sleep(10)
            return JsonResponse({'Status': False, 'Errors': 'Very bad request!'})
        db_token = ResetPasswordToken.objects.filter(user=user).first()
        # Если в базе нет токена для сброса у данного пользователя
        if not db_token:
            sleep(10)
            return JsonResponse({'Status': False, 'Errors': 'Very bad request!'})
        # И наконец и пользователь есть и токен есть, но токен из запроса не равен токену в базе
        if not token == db_token.key:
            sleep(10)
            return JsonResponse({'Status': False, 'Errors': 'Very bad request!'})

        # Если токены в запросе и БД совпадают, то открываем форму для ввода нового пароля
        form = EnterNewPasswordForm(initial={'token': self.request.query_params['token']})
        return render(request, 'backend/enter_new_password.html', {'form': form})

    # Запрос post в родительском классе корректно обрабатывает соответствие и логина и токена,
    # поэтому дополнительных проверок на соответствие как в get не требуется
    def post(self, request, *args, **kwargs):
        status = super(EnterNewPassword, self).post(request)
        # родительская функция класса ResetPasswordConfirm отработала хорошо
        # и могла бы отправить сигнал-письмо, но здесь нужно от неё нужны только проверки и обновление пароля,
        # т.к. от сигналов отказались в пользу celery - task
        if status.status_code == 200:
            return render(request, 'backend/success_enter_new_password.html')
        return status
