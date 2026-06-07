from django.urls import path

from marketplace import views

app_name = "marketplace"

urlpatterns = [
    path("", views.marketplace_home, name="home"),
    path("search/", views.marketplace_search, name="search"),
    path("locations/", views.location_suggestions, name="location_suggestions"),
    path("nearby/", views.nearby_properties, name="nearby_properties"),
    path("properties/<slug:slug>/", views.property_detail, name="property_detail"),
    path("properties/<slug:slug>/enquire/", views.property_enquiry, name="property_enquiry"),
    path("properties/<slug:slug>/review/", views.property_review, name="property_review"),
    path("owners/<str:username>/", views.owner_profile, name="owner_profile"),
]

