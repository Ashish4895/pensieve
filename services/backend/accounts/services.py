from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User


class AuthService:
    @staticmethod
    def register(email, password):
        return User.objects.create_user(email=email, password=password)

    @staticmethod
    def issue_tokens(user):
        refresh = RefreshToken.for_user(user)
        return {"access": str(refresh.access_token), "refresh": str(refresh)}
