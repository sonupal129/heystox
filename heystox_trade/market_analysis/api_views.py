from market_analysis.serializers import UserSerializer, UserProfileSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from .models import UserProfile
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework import status
from django.http import JsonResponse
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
# Code Starts Below

class UsersListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        print(request.META)
        users = UserProfile.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data)

    # def post(self, request):
    #     serializer = UserProfileSerializer(data=request.data)
    #     if serializer.is_valid():
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CustomTokenAuthentication(ObtainAuthToken):
    http_method_names = ["post"]

    def post(self, request):
        required_fields = ["username", "password"]
        data = request.data
        username = data.get("username", None)
        password = data.get("password", None)
        if not username or not password:
            return Response({"error": "username or password not provided in request"}, status=status.HTTP_206_PARTIAL_CONTENT)
        user = authenticate(request, username=username.lower(), password=password)
        if user and user.is_authenticated:
            token, is_created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key, "authenticated": True})
        else:
            return Response({"error": "wrong login credential provided please try again", "authenticated": False}, status=status.HTTP_407_PROXY_AUTHENTICATION_REQUIRED)


    