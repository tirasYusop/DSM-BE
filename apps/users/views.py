from django.contrib.auth import authenticate, get_user_model

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()

class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        if not username or not password:
            return Response(
                {"detail": "Username and password are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user is None:
            return Response(
                {"detail": "Invalid username or password."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if user.role == "volunteer" and not user.kitchen:
            return Response(
                {"detail": "This account is not linked to an active kitchen. Contact management."},
                status=status.HTTP_403_FORBIDDEN
            )

        refresh = RefreshToken.for_user(user)

        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
        }

        if user.role == "volunteer" and user.kitchen:
            user_data["kitchen"] = {
                "id": user.kitchen.id,
                "name": user.kitchen.name,
                "code": user.kitchen.code,
            }

        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": user_data
            },
            status=status.HTTP_200_OK
        )