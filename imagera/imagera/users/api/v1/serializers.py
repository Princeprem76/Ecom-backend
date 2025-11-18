from io import BytesIO
from django.contrib.auth import authenticate, login
import requests
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
import base64
from django.core import files
from django.conf import settings
# from config.settings.base import SOCIAL_AUTH_GOOGLE_OAUTH2_KEY
# from imagera.core.mixins import Facebook, Google
from imagera.core.utils import Util
from imagera.users.models import BusinessAccount, User
from django.template.loader import render_to_string
from pyotp import TOTP
from datetime import date
from rest_framework.exceptions import AuthenticationFailed, ValidationError

OTP_VALIDITY_TIME: int = 60 * 150


def get_base32_key(user) -> str:
    # Generates a base32 value based on the key provided.
    # Key used should be hashed value of password.
    key = settings.SECRET_KEY + str(user.id)
    key = bytes(key, encoding="UTF-8")
    val = base64.b32encode(key)
    val = str(val)
    return val.split("'")[1]


def generate_otp(user, digits=4) -> int:
    base32_key = get_base32_key(user)
    otp = TOTP(base32_key, interval=OTP_VALIDITY_TIME, digits=digits).now()
    return otp


def validate_otp(user, otp: int, digits=4) -> bool:
    base32_key = get_base32_key(user)
    return TOTP(base32_key, interval=OTP_VALIDITY_TIME, digits=digits).verify(otp)


class UserDetailsSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["email", "name", "user_image", "user_type", "email_verified"]


class JWTTokenSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(max_length=250)

    def validate(self, data):
        email = data.get("email", None)
        password = data.get("password", None)
        user = authenticate(email=email, password=password)
        if user is None:
            raise serializers.ValidationError("Invalid Credentials")
        return data

    def generate_token(self, validated_data):
        user_details = User.objects.get(email=validated_data["email"])
        token = RefreshToken.for_user(user_details)

        if user_details.email_verified == False:
            try:
                mail_subject = "Activate your account."
                message = render_to_string(
                    "emailtemplate.html",
                    {"otp": generate_otp(user_details)},
                )
                to_email = validated_data["email"]
                data = {
                    "email_body": message,
                    "to_email": to_email,
                    "subject": mail_subject,
                }
                Util.send_email(data)
            except:
                raise serializers.ValidationError("Can't send email!")
            raise serializers.ValidationError("Email Verification OTP has been sent!")

        user_serializer = UserDetailsSerializer(user_details, many=False)
        social_auth = bool(user_details.social_auth)
        personal_info_added = bool(user_details.name) and bool(user_details.dob)
        response = {
            "social_auth": social_auth,
            "personal_info": personal_info_added,
            "user_details": user_serializer.data,
            "refresh": str(token),
            "access": str(token.access_token),
        }
        return response


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(max_length=250, write_only=True)
    re_password = serializers.CharField(max_length=250, write_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "password", "re_password", "dob"]

    def validate(self, data):
        email = data.get("email", None)
        password = data.get("password", None)
        re_password = data.get("re_password", None)
        dob = data.get("dob")
        if password != re_password:
            raise serializers.ValidationError("Password and Re-Password does not match")
        today = date.today()
        age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        if age < 13:
            raise serializers.ValidationError("User must be at least 13 years old")
        return data

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            dob=validated_data["dob"],
        )
        try:
            mail_subject = "Activate your account."
            message = render_to_string(
                "otp_verification_template.html",
                {"user": user, "otp": generate_otp(user)},
            )
            print(generate_otp(user))
            to_email = validated_data["email"]
            data = {"email_body": message, "email": to_email, "subject": mail_subject}
            Util.send_email(data)
        except:
            raise serializers.ValidationError("Can't send email!")
        return user


class UserVerifySerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True, required=True)
    otp = serializers.CharField(max_length=4, write_only=True)

    def create(self, validated_data):
        email = self.validated_data["email"]
        otp = self.validated_data["otp"]
        try:
            user = User.objects.get(email=email, email_verified=False)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist!")
        if not validate_otp(user, otp):
            raise serializers.ValidationError({"otp": "Invalid code."})
        user.email_verified = True
        user.save()
        refresh = self.get_token(user)
        data = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        return data

    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)


class UserObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        exclude = [
            "social_auth",
            "is_active",
            "is_staff",
            "password",
            "is_superuser",
            "groups",
            "user_permissions",
            "last_login",
        ]
        read_only_fields = [
            "email",
            "email_verified",
            "user_type",
        ]


class UpdatePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=250, write_only=True)
    password = serializers.CharField(max_length=250, write_only=True)
    re_password = serializers.CharField(max_length=250, write_only=True)

    def validate(self, data):
        old_password = data.get("old_password", None)
        password = data.get("password", None)
        re_password = data.get("re_password", None)
        if password != re_password:
            raise serializers.ValidationError("Password and Re-Password does not match")

        user = self.context["request"].user
        if not user.check_password(old_password):
            raise serializers.ValidationError("Old password is incorrect.")

        return data

    def update(self, validated_data):
        user = self.context["request"].user
        user.set_password(validated_data["password"])
        user.save()
        return user


class UpgradeBusinessUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = BusinessAccount
        fields = "__all__"
        extra_kwargs = {
            "business_verified": {"read_only": True},
            "client": {"read_only": True},
        }

    def validate(self, data):
        business_certificate = data.get("business_certificate", None)
        if business_certificate == None:
            raise serializers.ValidationError("Business Certifcate proof not provided!")
        return data

    def update(self, validated_data):
        user = self.context["request"].user
        business_account = BusinessAccount.objects.create(client=user, **validated_data)
        return user


class VerifyBusinessAccountSerializer(serializers.ModelSerializer):
    client_id = serializers.CharField(max_length=150, write_only=True)
    client = UserObjectSerializer()

    class Meta:
        model = BusinessAccount
        fields = [
            "id",
            "client",
            "business_name",
            "business_certificate",
            "client_identity",
            "business_number",
            "business_verified",
            "client_id",
        ]

    def create(self, validated_data):
        client_id = self.validated_data["client_id"]
        business_account = BusinessAccount.objects.get(client_id=client_id)
        business_account.business_verified = True
        business_account.save()
        return business_account


class ForgetPasswordResetEmailSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True, required=True)
    otp = serializers.CharField(max_length=4, write_only=True)

    def validate(self, data):
        email = data.get("email")
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist!")
        return data

    def send_email(self, validated_data):
        try:
            mail_subject = "Reset Account Password."
            message = render_to_string(
                "reset_password_otp.html",
                {"user": self.user, "otp": generate_otp(self.user)},
            )
            to_email = data["email"]
            data = {"email_body": message, "email": to_email, "subject": mail_subject}

            Util.send_email(data)
        except:
            raise serializers.ValidationError("Can't send email!")

    def verify_otp(self, validated_data):
        user = self.user
        otp = self.validated_data["otp"]
        if not validate_otp(user, otp):
            raise serializers.ValidationError({"otp": "Invalid code."})
        refresh = self.get_token(user)
        response = {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        return response

    @classmethod
    def get_token(cls, user):
        return RefreshToken.for_user(user)


class ForgetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=250, write_only=True)
    re_password = serializers.CharField(max_length=250, write_only=True)

    def validate(self, data):
        old_password = data.get("old_password", None)
        password = data.get("password", None)
        re_password = data.get("re_password", None)
        if password != re_password:
            raise serializers.ValidationError("Password and Re-Password does not match")

        return data

    def save(self, validated_data):
        user = self.context["request"].user
        user.set_password(validated_data["password"])
        user.save()
        return user


# class GoogleAuthSerializer(serializers.Serializer):
#     id_token = serializers.CharField(write_only=True)

#     @classmethod
#     def get_token(cls, user):
#         return RefreshToken.for_user(user)

#     def get_user_details(self, user):
#         refresh = self.get_token(user)
#         user_serializer = UserDetailsSerializer(user, many=False)
#         social_auth = bool(user.social_auth)
#         personal_info_added = bool(user.name) and bool(user.dob)
#         response = {
#             "social_auth": social_auth,
#             "personal_info": personal_info_added,
#             "user_details": user_serializer.data,
#             "refresh": str(refresh),
#             "access": str(refresh.access_token),
#         }
#         return response

#     def validate(self, data):
#         id_token = data.pop("id_token")
#         user_data = Google.validate(id_token)
#         try:
#             user_data["sub"]
#         except Exception:
#             raise serializers.ValidationError(
#                 {"id_token": ["The token is invalid or expired. Please login again."]}
#             )
#         if user_data["aud"] != SOCIAL_AUTH_GOOGLE_OAUTH2_KEY:
#             raise AuthenticationFailed("Invalid Google oauth key")

#         email = user_data["email"]
#         name = user_data["name"]
#         social_auth_provider = "GOOGLE"
#         url = user_data.get("picture", None)
#         file_name = None
#         if url is not None:
#             picture = requests.get(url.replace("=s96-c", "=s200-c"))
#             # Get the filename from the url, used for saving later
#             file_name = url.split("/")[-1].replace("=s96-c", "=s200-c") + ".jpeg"
#             picture_temp = BytesIO()
#             # Read the streamed image
#             picture_temp.write(picture.content)

#         user = User.objects.filter(email=email).first()

#         if user:
#             user_details = self.get_user_details(user)
#             return user_details
#         else:
#             user = User.objects.create(
#                 email=email, name=name, social_auth=social_auth_provider
#             )
#             user.email_verified = True
#             user.save()
#             user_details = self.get_user_details(user)
#             if file_name:
#                 user.user_image.save(file_name, files.File(picture_temp))
#             return user_details


# class FacebookAuthSerializer(serializers.Serializer):
#     """Handles serialization of facebook related data"""

#     auth_token = serializers.CharField(write_only=True)
#     profile_pic_url = serializers.ImageField(source="profile_pic", read_only=True)

#     @classmethod
#     def get_token(cls, user):
#         return RefreshToken.for_user(user)

#     def get_user_details(self, user):
#         refresh = self.get_token(user)
#         user_serializer = UserDetailsSerializer(user, many=False)
#         social_auth = bool(user.social_auth)
#         personal_info_added = bool(user.name) and bool(user.dob)
#         response = {
#             "social_auth": social_auth,
#             "personal_info": personal_info_added,
#             "user_details": user_serializer.data,
#             "refresh": str(refresh),
#             "access": str(refresh.access_token),
#         }
#         return response

#     def validate_auth_token(self, auth_token):
#         user_data = Facebook.validate(auth_token)
#         try:
#             id = user_data["id"]
#             if "email" in user_data:
#                 email = user_data["email"]
#             else:
#                 email = id + "@mountemart.com.np"
#             name = user_data["name"]
#             social_auth_provider = "FACEBOOK"
#             current_user_data = User.objects.filter(email=email)
#             url = f"https://graph.facebook.com/{id}/picture?type=large"
#             picture = requests.get(url)
#             # Get the filename from the url, used for saving later
#             file_name = url.split("/")[-2] + ".jpeg"
#             picture_temp = BytesIO()
#             # Read the streamed image
#             picture_temp.write(picture.content)

#             if current_user_data.exists():
#                 user_details = self.get_user_details(current_user_data.first())
#                 return user_details
#             else:
#                 age_range = user_data.get("age_range", None)
#                 if age_range is not None and age_range.get("min", 0) < 13:
#                     raise ValidationError("User must be at least 13 years old.")
#                 user = User.objects.create(
#                     email=email, name=name, social_auth=social_auth_provider
#                 )
#                 user.email_verified = True
#                 user.save()
#                 user.user_image.save(file_name, files.File(picture_temp))
#                 user_details = self.get_user_details(user)
#                 return user_details

#         except Exception:
#             raise ValidationError(
#                 "The token  is invalid or expired. Please login again."
#             )
