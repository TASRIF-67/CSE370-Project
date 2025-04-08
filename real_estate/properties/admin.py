from django.contrib import admin
from .models import CustomUser, Property, PropertyImage, Interest, Transaction, Feedback

admin.site.register(CustomUser)
admin.site.register(PropertyImage)
admin.site.register(Interest)
admin.site.register(Transaction)
admin.site.register(Feedback)

@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ('title', 'seller', 'status', 'assigned_agent')
    list_filter = ('status', 'property_type')