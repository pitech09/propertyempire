from django.contrib import admin
from .models import Tenant, House, Payment, FlatBuilding, RentCharge, Issue
from django.contrib.auth.models import Group
from rest_framework.authtoken.models import Token
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.db import transaction

from tennants.services.tenant_accounts import create_tenant_login_user, send_tenant_credentials_sms

admin.site.site_header = 'House Administration'


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):

    list_display = ('user','full_name', 'email', 'phone', 'house', 'rent', 'security_deposit', 'balance','building_name')
    ordering = ('full_name',)
    readonly_fields = ('rent', 'security_deposit', 'balance','user')

    def deposit_amount(self, obj):
        return obj.security_deposit
    deposit_amount.short_description = 'Security Deposit'

    def building_name(self, obj):
        return obj.building_name
    building_name.short_description = 'Building Name'

    def rent_amount(self, obj):
        return obj.rent
    rent_amount.short_description = 'Monthly Rent'


    def save_model(self, request, obj, form, change):
        password = None
        if not change and obj.user_id is None:
            obj.user, password = create_tenant_login_user(
                obj.full_name,
                email=obj.email,
                phone=obj.phone,
                id_number=obj.id_number,
            )
            obj._skip_welcome_sms = True

        super().save_model(request, obj, form, change)

        if password:
            login_url = request.build_absolute_uri("/login/")
            transaction.on_commit(
                lambda: send_tenant_credentials_sms(obj, password, login_url=login_url)
            )

@admin.register(House)
class HouseAdmin(admin.ModelAdmin):
    list_display = ('house_number', 'flat_building', 'house_size', 'house_rent_amount', 'deposit_amount', 'occupation')
    readonly_fields = ( 'occupation',)
    list_filter = ('flat_building', 'occupation')
    search_fields = ('house_number', 'flat_building__building_name')


    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'payment_method','paid_at', 'rent_charge', 'payment_reference',"amount")
    readonly_fields = ('amount', 'balance',)

    def house(self, obj):
        return obj.tenant.house.house_number if obj.tenant and obj.tenant.house else None

    def balance(self, obj):
        return obj.balance
    balance.short_description = 'Balance'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

@admin.register(FlatBuilding)
class FlatBuildingAdmin(admin.ModelAdmin):
    list_display = ('user','building_name', 'address', 'number_of_houses', 'how_many_occupied', 'vacant_houses','tenant_count')
    search_fields = ('biulding_name', 'address')
    readonly_fields = ('how_many_occupied', 'vacant_houses')

    def how_many_occupied(self, obj):
        return obj.how_many_occupied
    how_many_occupied.short_description = 'Occupied Houses'

    def tenant_count(self, obj):
        return obj.tenant_count()
    tenant_count.short_description = 'Number of Tenants'


    def vacant_houses(self, obj):
        return obj.vacant_houses
    vacant_houses.short_description = 'Vacant Houses'

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

@admin.register(RentCharge)
class RentChargeAdmin(admin.ModelAdmin):
    list_display = ('tenant', 'year', 'is_paid', 'month', 'amount_due')
    list_filter = ('month', 'year')
    ordering = ('-year',)
    search_fields = ('tenant__full_name',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


@admin.register(Issue)
class IssueAdmin(admin.ModelAdmin):
    list_display = ("title", "tenant", "house", "building", "status", "created_at")
    list_filter = ("status", "tenant__house__flat_building")
    search_fields = (
        "title",
        "description",
        "tenant__full_name",
        "tenant__house__house_number",
        "tenant__house__flat_building__building_name",
    )
    readonly_fields = ("tenant", "title", "description", "created_at")
    list_select_related = ("tenant", "tenant__house", "tenant__house__flat_building")
    ordering = ("-created_at",)

    def house(self, obj):
        return obj.tenant.house if obj.tenant and obj.tenant.house else "-"

    def building(self, obj):
        if obj.tenant and obj.tenant.house and obj.tenant.house.flat_building:
            return obj.tenant.house.flat_building.building_name
        return "-"
