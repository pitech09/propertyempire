from rest_framework import serializers
from .models import Tenant, House, Payment, FlatBuilding, RentCharge
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()





class TenantSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Tenant
        fields = '__all__'

    def validate_house(self, house):
        request = self.context.get("request")
        if house and request and house.user_id != request.user.id:
            raise serializers.ValidationError("You can only assign tenants to your own houses.")
        return house

class HouseSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = House
        fields = '__all__'

    def validate(self, attrs):
        request = self.context.get("request")
        building = attrs.get("flat_building") or getattr(self.instance, "flat_building", None)
        if building and request and building.user_id != request.user.id:
            raise serializers.ValidationError("You can only use your own buildings.")
        return attrs
    
class FlatBuildingSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = FlatBuilding
        fields = '__all__'

class PaymentSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Payment
        fields = '__all__'

    def validate(self, attrs):
        request = self.context.get("request")
        tenant = attrs.get("tenant") or getattr(self.instance, "tenant", None)
        rent_charge = attrs.get("rent_charge") or getattr(self.instance, "rent_charge", None)

        if request:
            if tenant and (not tenant.house or tenant.house.user_id != request.user.id):
                raise serializers.ValidationError("You can only record payments for your own tenants.")
            if rent_charge and (
                not rent_charge.tenant.house or rent_charge.tenant.house.user_id != request.user.id
            ):
                raise serializers.ValidationError("You can only use your own rent charges.")
        if tenant and rent_charge and tenant != rent_charge.tenant:
            raise serializers.ValidationError("Payment tenant must match rent charge tenant.")
        return attrs

class RegisterAdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    phone = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = User
        fields = ['username', 'password', 'email', 'first_name', 'last_name', 'phone']

    def create(self, validated_data):
        phone = validated_data.pop("phone", None)
        user = User(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        user.set_password(validated_data['password'])
        user.is_staff = True
        user.save()
        if phone:
            from tennants.models import LandlordProfile
            LandlordProfile.objects.create(user=user, phone=phone)
        return user

class ForgotPasswordSerializer(serializers.Serializer):
    username = serializers.CharField()
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def save(self):
        username = self.validated_data['username']
        new_password = self.validated_data['new_password']
        otp = self.validated_data['otp']

        user = User.objects.get(username=username)

        # TODO: validate OTP here

        user.set_password(new_password)
        user.save()
        return user


class AdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)
    remember_me = serializers.BooleanField(default=False)
    token = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)

    def validate(self, data):
        from django.contrib.auth import authenticate
        from rest_framework_simplejwt.tokens import RefreshToken

        username = data.get('username')
        password = data.get('password')
        user = authenticate(username=username, password=password)

        if user is None or not user.is_staff:
            raise serializers.ValidationError("Invalid credentials or not an admin user")

        refresh = RefreshToken.for_user(user)
        data['token'] = str(refresh.access_token)
        data['refresh'] = str(refresh)
        return data

class RentChargeSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = RentCharge
        fields = '__all__'

    def validate_tenant(self, tenant):
        request = self.context.get("request")
        if tenant and request and (not tenant.house or tenant.house.user_id != request.user.id):
            raise serializers.ValidationError("You can only create rent charges for your own tenants.")
        return tenant
