from rest_framework.serializers import (
    CharField,
    ModelSerializer,
    ValidationError
)

from django.core.management.base import CommandError
from django.contrib.auth import get_user_model
User = get_user_model()

######################################################
class UserLoginSerializer(ModelSerializer):

    username = CharField()
    token = CharField(allow_blank=True,read_only=True)

    class Meta:
        model = User
        fields = [
            'username',
            'password',
            'token',
        ]

        extra_kwargs = {
                "password": {
                    "write_only": True
                }
        }

    ##########################################
    def validate(self,data):

        user_obj = None
        username = data.get("username",None)
        password = data["password"]

        if not username:
            raise ValidationError("A username is requiered")

        user = User.objects.filter(username=username).distinct()

        if user.exists():
            user_obj = user.first()
        else:
            raise ValidationError("User is not valid")

        if user_obj:
            if not user_obj.check_password(password):
                raise  ValidationError("Incorect password ")

        data["token"] = "aaaaaa"
        return data

######################################################
class UserListSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = '__all__'

######################################################
class UserUpdateSerializer(ModelSerializer):
    class Meta:
        model  = User
        fields = '__all__'

######################################################
class UserDeleteSerializer(ModelSerializer):

    class Meta:
        model = User
        fields =  ['username']

        def delete(self,validated_data):
            username = validated_data['username']

            try:
                User.get(username=username).delete()
            except User.DoesNotExist:
                print("User does not exists")


######################################################
class UserCreateSerializer(ModelSerializer):
    class Meta:
        model = User
        fields = [
            'username',
            'password',
            'is_staff',
            'first_name',
            'last_name'
        ]

        extra_kwargs = {
                "password": {
                    "write_only": True
                }
        }

    #########################################
    def create(self,validated_data):
        username     = validated_data['username']
        password     = validated_data['password']
        firstname    = validated_data['first_name']
        lastname     = validated_data['last_name']
        is_staff     = validated_data['is_staff']
        user_obj = User(
            username   = username,
            first_name = firstname,
            last_name  = lastname,
            is_staff   = is_staff
        )
        user_obj.set_password(password)
        user_obj.save()
        return validated_data

