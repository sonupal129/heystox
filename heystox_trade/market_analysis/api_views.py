from market_analysis.serializers import UserSerializer, UserProfileSerializer, SortedStockDashboardSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from .models import UserProfile, SortedStocksList
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework import status
from django.http import JsonResponse
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from datetime import datetime
# Code Starts Below

class UsersListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        users = UserProfile.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

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


class SortedStocksListView(APIView):
    http_method_names = ["get"]

    def get(self, request, symbol=None):
        date = request.GET.get("created_at")
        requested_date = None
        if date:
            requested_date = datetime.strptime(date, "%Y-%m-%d").date()
        if symbol and requested_date:
            sorted_stocks = SortedStocksList.objects.get(symbol__symbol=symbol, created_at__date=requested_date)
            serializer = SortedStockDashboardSerializer(sorted_stocks)
            return Response(serializer.data, status=status.HTTP_200_OK)
        elif symbol:
            sorted_stocks = SortedStocksList.objects.filter(symbol__symbol=symbol)
        elif requested_date:
            sorted_stocks = SortedStocksList.objects.filter(created_at__date=requested_date).order_by("symbol__symbol")
        else:
            sorted_stocks = SortedStocksList.objects.filter(created_at__date=datetime.today().date()).order_by("symbol__symbol")
        serializer = SortedStockDashboardSerializer(sorted_stocks, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)