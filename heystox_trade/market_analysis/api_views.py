from market_analysis.serializers import UserSerializer, UserProfileSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated
from .models import UserProfile
from rest_framework.response import Response
from rest_framework.parsers import JSONParser
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework import status
from django.http import JsonResponse
# Code Starts Below

class UsersListView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        users = UserProfile.objects.all()
        serializer = UserProfileSerializer(users, many=True)
        return Response(serializer.data)

    # def post(self, request):
    #     serializer = UserProfileSerializer(data=request.data)
    #     if serializer.is_valid():
    #         return Response(serializer.data, status=status.HTTP_201_CREATED)
    #     return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


