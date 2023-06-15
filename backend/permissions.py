from rest_framework.permissions import BasePermission


# Права на CRUD операции только у владельца и у админа
# [Фильтрация(права) для get реализованы переопределением метода get_queryset в ViewSet]
from backend.models import Product


class IsOwnerAdminOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user  # or request.user.is_staff


# Чтобы посмотреть владельца редактируемого объекта, пришлось сделать вложенный запрос к БД
# Продукт принадлежит магазину - магазин пользователю. И именно оператор in отработал верно!
class IsOwnerOrAdmin(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj in Product.objects.filter(product_infos__shop_id__user_id=request.user.id) \
               or request.user.is_staff