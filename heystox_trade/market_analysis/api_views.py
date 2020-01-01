from market_analysis.serializers import UserSerializer
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated

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
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@csrf_exempt
def users_view(request):
    if request.method == "GET":
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return JsonResponse(serializer.data, safe=False)
    elif request.method == "POST":
        post_data = JSONParser().parse(request)
        serializer = UserSerializer(data=post_data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)

@csrf_exempt  
def user_detail_view(request, pk):
    try:
        instance = User.objects.get(id=pk)
    except User.DoesNotExist:
        return JsonResponse({"error": "User Id is not available"}, status=404)
    if request.method == "GET":
        serializer = UserSerializer(instance)
        return JsonResponse(serializer.data)
    elif request.method == "PUT":
        post_data = JSONParser().parse(request)
        serializer = UserSerializer(instance, data=post_data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=200)
        return JsonResponse(serializer.errors, status=400)
    elif request.method == "DELETE":
        instance.delete()
        return JsonResponse({"succesfull":"User Deleted Successfully"}, status=204)


