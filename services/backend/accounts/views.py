from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.status import HTTP_201_CREATED, HTTP_401_UNAUTHORIZED
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.serializers import (
    AccessResponseSerializer,
    AuthResponseSerializer,
    EmptySerializer,
    EmptyResponseSerializer,
    ErrorResponseSerializer,
    LoginSerializer,
    RegisterSerializer,
    UserResponseSerializer,
    UserSerializer,
)
from accounts.services import AuthService
from core.api import api_error, api_success

REFRESH_COOKIE = "refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth/"
CSRF_HEADER = OpenApiParameter(
    "X-CSRFToken",
    str,
    OpenApiParameter.HEADER,
    required=True,
    description="Must match the csrftoken cookie returned by register or login.",
)
REFRESH_COOKIE_PARAMETER = OpenApiParameter(
    REFRESH_COOKIE,
    str,
    OpenApiParameter.COOKIE,
    required=True,
    description="HttpOnly refresh token cookie set by register, login, or refresh.",
)


class CSRFCookieAuthentication(SessionAuthentication):
    def authenticate(self, request):
        # Bootstrap POST /refresh/ has no cookies yet — enforce CSRF only when
        # a refresh cookie is present (real session mutation).
        if request.COOKIES.get(REFRESH_COOKIE):
            self.enforce_csrf(request)
        return None


def _set_refresh_cookie(response, token):
    response.set_cookie(
        REFRESH_COOKIE,
        token,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=getattr(settings, "SECURE_COOKIES", False),
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


@method_decorator(ensure_csrf_cookie, name="dispatch")
class RegisterView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    @extend_schema(
        responses={
            201: OpenApiResponse(
                AuthResponseSerializer,
                description="Registered; sets refresh and csrftoken cookies.",
            ),
            400: ErrorResponseSerializer,
        }
    )
    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        return _token_response(serializer.save(), HTTP_201_CREATED)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class LoginView(GenericAPIView):
    permission_classes = (AllowAny,)
    serializer_class = LoginSerializer

    @extend_schema(
        responses={
            200: OpenApiResponse(
                AuthResponseSerializer,
                description="Authenticated; sets refresh and csrftoken cookies.",
            ),
            400: ErrorResponseSerializer,
        }
    )
    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        return _token_response(serializer.validated_data["user"])


class RefreshView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = (JWTAuthentication, CSRFCookieAuthentication)
    serializer_class = TokenRefreshSerializer

    @extend_schema(
        auth=[],
        request=None,
        parameters=[REFRESH_COOKIE_PARAMETER, CSRF_HEADER],
        responses={
            200: OpenApiResponse(
                AccessResponseSerializer,
                description="Token refreshed; rotates the refresh cookie.",
            ),
            401: ErrorResponseSerializer,
            403: ErrorResponseSerializer,
        },
    )
    def post(self, request):
        token = request.COOKIES.get(REFRESH_COOKIE)
        if not token:
            return api_error("Refresh token required", status_code=HTTP_401_UNAUTHORIZED)

        serializer = self.serializer_class(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as exc:
            raise InvalidToken(exc.args[0]) from exc
        response = api_success(
            {"access": serializer.validated_data["access"]},
            message="Token refreshed",
        )
        return _set_refresh_cookie(
            response, serializer.validated_data.get("refresh", token)
        )


class LogoutView(GenericAPIView):
    permission_classes = (AllowAny,)
    authentication_classes = (JWTAuthentication, CSRFCookieAuthentication)
    serializer_class = EmptySerializer

    @extend_schema(
        auth=[],
        request=None,
        parameters=[
            OpenApiParameter(
                REFRESH_COOKIE,
                str,
                OpenApiParameter.COOKIE,
                required=False,
                description="Refresh token cookie to blacklist and clear.",
            ),
            CSRF_HEADER,
        ],
        responses={
            200: OpenApiResponse(
                EmptyResponseSerializer,
                description="Logged out; clears the refresh cookie.",
            ),
            403: ErrorResponseSerializer,
        },
    )
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

    @extend_schema(responses={200: UserResponseSerializer, 401: ErrorResponseSerializer})
    def get(self, request):
        return api_success(UserSerializer(request.user).data)
