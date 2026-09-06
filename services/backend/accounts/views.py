from django.conf import settings
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import (
    EmptySerializer,
    LoginSerializer,
    RegisterSerializer,
    UserSerializer,
)
from accounts.services import AuthService
from core.api import api_error, api_success

REFRESH_COOKIE = "refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth/"


def _set_refresh_cookie(response, token):
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=not settings.DEBUG,
        samesite="Lax",
        path=REFRESH_COOKIE_PATH,
    )
    return response


def _token_response(user, status_code=200):
    tokens = AuthService.issue_tokens(user)
    response = api_success(
        {"access": tokens["access"], "user": UserSerializer(user).data},
        message="Authenticated",
        status_code=status_code,
    )
    return _set_refresh_cookie(response, tokens["refresh"])


class RegisterView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _token_response(serializer.save(), HTTP_201_CREATED)


class LoginView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return _token_response(serializer.validated_data["user"])


class RefreshView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = TokenRefreshSerializer

    def post(self, request):
        token = request.COOKIES.get(REFRESH_COOKIE)
        if not token:
            return api_error("Refresh token required", status_code=HTTP_401_UNAUTHORIZED)

        serializer = self.serializer_class(data={"refresh": token})
        serializer.is_valid(raise_exception=True)
        response = api_success(
            {"access": serializer.validated_data["access"]},
            message="Token refreshed",
        )
        return _set_refresh_cookie(
            response, serializer.validated_data.get("refresh", token)
        )


class LogoutView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = EmptySerializer

    def post(self, request):
        token = request.COOKIES.get(REFRESH_COOKIE)
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass
        response = api_success(message="Logged out")
        response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)
        return response


class MeView(GenericAPIView):
    permission_classes = (IsAuthenticated,)
    serializer_class = UserSerializer

    def get(self, request):
        return api_success(UserSerializer(request.user).data)
