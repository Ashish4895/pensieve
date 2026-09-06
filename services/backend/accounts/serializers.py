from django.contrib.auth import authenticate, password_validation
from rest_framework import serializers

from accounts.models import User
from accounts.services import AuthService


class EmptySerializer(serializers.Serializer):
    pass


class ErrorResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=False)
    message = serializers.CharField()
    data = serializers.JSONField(allow_null=True)
    errors = serializers.JSONField(allow_null=True)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "role")


class AuthDataSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = UserSerializer()


class AuthResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = AuthDataSerializer()
    errors = serializers.JSONField(allow_null=True)


class AccessDataSerializer(serializers.Serializer):
    access = serializers.CharField()


class AccessResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = AccessDataSerializer()
    errors = serializers.JSONField(allow_null=True)


class EmptyResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = serializers.JSONField(allow_null=True)
    errors = serializers.JSONField(allow_null=True)


class UserResponseSerializer(serializers.Serializer):
    success = serializers.BooleanField(default=True)
    message = serializers.CharField()
    data = UserSerializer()
    errors = serializers.JSONField(allow_null=True)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_password(self, value):
        password_validation.validate_password(value)
        return value

    def create(self, validated_data):
        return AuthService.register(**validated_data)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(
            request=self.context.get("request"),
            email=attrs["email"],
            password=attrs["password"],
        )
        if user is None:
            raise serializers.ValidationError("Invalid email or password.")
        attrs["user"] = user
        return attrs
