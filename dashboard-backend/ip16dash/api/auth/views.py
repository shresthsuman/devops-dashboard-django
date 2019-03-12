import json
import datetime
import re
import os
import sys

from rest_framework.views    import APIView
from rest_framework.generics import (
   ListAPIView,
   CreateAPIView,
   DestroyAPIView,
   RetrieveAPIView,
   UpdateAPIView,
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)


from django.http               import HttpResponse
from rest_framework            import status
from rest_framework            import permissions
from rest_framework.response   import Response
from rest_framework.status     import HTTP_200_OK, HTTP_400_BAD_REQUEST
from rest_framework.response   import Response
from rest_framework.decorators import api_view
from rest_framework.parsers    import JSONParser
from rest_framework.renderers  import JSONRenderer
from django.db                 import connection

from .serializers              import (
    UserCreateSerializer,
    UserLoginSerializer,
    UserDeleteSerializer,
    UserListSerializer,
    UserUpdateSerializer,
)

from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAdminUser,
    IsAuthenticatedOrReadOnly,
)
from pprint import pprint
from django.contrib.auth import get_user_model
User = get_user_model()

import django
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

########################################################
############## API CLASSES #############################
########################################################

############################################
class UserLogin(APIView):

    permission_classes = [AllowAny]
    serializer_class = UserLoginSerializer

    def post(self,request,*args,**kwargs):
        data = request.data
        serializer = UserLoginSerializer(data=data)
        if serializer.is_valid(raise_exception=True):
            new_data = serializer.data
            return Response(new_data, status=HTTP_200_OK)
        return Response(serializer.errors, status=HTTP_400_BAD_REQUEST)

############################################
#class UserCreate(CreateAPIView):

#class UserCreate(APIView):
class UserCreate(CreateAPIView):

    queryset = User.objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = [IsAdminUser]

    #def perform_create(self,serializer):
    #    print(self.request.user)
    #    serializer.save()

    #def post(self,request,*args,**kwargs):
    #    return
    #     data = request.data
    #     print(self.request.user)
    #     pprint(data)


    #    serializer = UserCreateSerializer()
    #    new_data = serializer.data
    #    return Response(new_data, status=HTTP_200_OK)


############################################
class UserDelete(DestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserDeleteSerializer
    lookup_field = 'username'

###########################################
class UserList(ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserListSerializer

###########################################
class UserUpdate(UpdateAPIView):
    queryset = User.objects.all()
    serializer_class = UserUpdateSerializer
    lookup_field = 'username'