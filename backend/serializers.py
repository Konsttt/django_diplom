from drf_spectacular.utils import extend_schema_serializer, OpenApiExample
from rest_framework import serializers

from backend.models import User, Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order, Contact


#  region api_documentation
@extend_schema_serializer(
    exclude_fields=('id', 'structure', 'building'),
    examples=[
        OpenApiExample(
            'Valid example 1',
            summary='CRUD только своих контактов. Просмотр всех контактов менеджером.',
            value={
                'city': 'Москва',
                'street': 'Садовая',
                'house': '5',
                'apartment': '1',
                'phone': '1234567',
                'user': 1,
            },
            request_only=True,  # signal that example only applies to requests
            response_only=False,  # signal that example only applies to responses
        ),
    ])
# endregion
class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ('id', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'user', 'phone')
        read_only_fields = ('id',)
        extra_kwargs = {
            'user': {'write_only': True}
        }


#  region api_documentation
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Example 1',
            summary='Создание нового пользователя. (Новая запись в БД в таблице backend_users)',
            value={
                'email': 'user3@tips-tricks.ru',
                'password': 'Qqq111!!!',
                'first_name': 'User3',
                'last_name': 'Userovich3',
                'phone': '123456789',
                'company': 'SpaceX',
                'position': 'python backend',
            },
            request_only=True,  # signal that example only applies to requests
            response_only=False,  # signal that example only applies to responses
        ),
    ])
# endregion
class UserSerializer(serializers.ModelSerializer):
    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'password', 'company', 'position', 'contacts')
        read_only_fields = ('id',)


# Данный сериалайзер применяется только в drf-spectacular
#  region api_documentation
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Пример:',
            summary='Логин пользователя по email и паролю',
            value={
                'email': 'user3@tips-tricks.ru',
                'password': 'Qqq111!!!',
            },
            # request_only=True,  # signal that example only applies to requests
            # response_only=False,  # signal that example only applies to responses
        ),
    ])
# endregion
class LoginSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('email', 'password')


#  region api_documentation
@extend_schema_serializer(
    examples=[
        OpenApiExample(
            'Пример:',
            summary='Изменение названия Категории товаров',
            value={
                'name': 'SSD диски',
            },
        ),
    ])
# endregion
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ('id', 'name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):
    class Meta:
        model = Shop
        fields = ('id', 'name', 'state',)
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    # category = serializers.StringRelatedField()

    class Meta:
        model = Product
        fields = ('name', 'category',)


class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value',)


class ProductInfoSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'model', 'product', 'shop', 'quantity', 'price', 'price_rrc', 'product_parameters',)
        read_only_fields = ('id',)


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'product_info', 'quantity', 'order',)
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }


class OrderItemCreateSerializer(OrderItemSerializer):
    product_info = ProductInfoSerializer(read_only=True)

#  region api_documentation
@extend_schema_serializer(
    exclude_fields=('total_sum',),
    examples=[
         OpenApiExample(
            'Valid example 1',
            summary='Создание Заказа из Корзины',
            value={'id': "5", 'contact': 4},
         ),
    ]
)
# endregion
class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemCreateSerializer(read_only=True, many=True)

    total_sum = serializers.IntegerField()
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'state', 'dt', 'total_sum', 'contact',)
        read_only_fields = ('id',)
