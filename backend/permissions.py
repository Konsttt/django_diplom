from rest_framework.permissions import BasePermission


# Права на CRUD операции только у владельца и у админа
# [Фильтрация(права) для get реализованы переопределением метода get_queryset в ContactViewSet]
class IsOwnerAdminOrReadOnly(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user == obj.user or request.user.is_staff
