# real_estate/urls.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from properties import views
from properties.views import CustomLoginView

urlpatterns = [
    path('', views.home, name='home'),
    path('about/', views.about_us, name='about_us'),
    path('agent/interests/', views.agent_interests, name='agent_interests'),
    path('signup/', views.normal_signup, name='normal_signup'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('property/create/', views.create_property, name='create_property'),
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
  path('admin/property/<int:property_id>/view/', views.admin_view_property, name='admin_view_property'),
   path('property/<int:property_id>/edit/', views.edit_property, name='edit_property'),
    path('property/<int:property_id>/delete/', views.delete_property, name='delete_property'),
    path('property/<int:property_id>/view/', views.view_property, name='view_property'),
    path('property/<int:property_id>/', views.property_detail, name='property_detail'),
    path('property/<int:property_id>/edit/', views.edit_property, name='edit_property'),
    path('property/<int:property_id>/delete/', views.delete_property, name='delete_property'),
    path('property/<int:property_id>/admin/edit/', views.admin_edit_property, name='admin_edit_property'),
    path('property/<int:property_id>/admin/delete/', views.admin_delete_property, name='admin_delete_property'),
    path('property/<int:property_id>/interest/', views.express_interest, name='express_interest'),
    path('property/<int:property_id>/confirm/', views.confirm_transaction, name='confirm_transaction'),
   path('property/<int:property_id>/status/', views.update_property_status, name='update_property_status'),
    path('feedback/', views.submit_feedback, name='submit_feedback'),
    path('profile/update/', views.update_profile, name='update_profile'),
    path('users/manage/', views.manage_users, name='manage_users'),
    path('users/<int:user_id>/detail/', views.user_detail, name='user_detail'),
    path('users/<int:user_id>/edit/', views.edit_user, name='edit_user'),
    path('users/<int:user_id>/delete/', views.delete_user, name='delete_user'),
    path('admin/create/', views.create_admin, name='create_admin'),
   path('admin/agent-assignments/', views.admin_agent_assignments, name='admin_agent_assignments'),
   # Add this to your existing urlpatterns
   path('property/<int:property_id>/express-interest/', views.express_interest, name='express_interest'),
    path('property/<int:property_id>/remove-interest/', views.remove_interest, name='remove_interest'),
path('interest/<int:interest_id>/contact-agent/', views.contact_agent, name='contact_agent'),
    path('property/<int:property_id>/approve/', views.approve_property, name='approve_property'),
    path('property/<int:property_id>/sold/', views.mark_sold, name='mark_sold'),
    path('admin/remove/<int:user_id>/', views.remove_admin, name='remove_admin'),
    path('agent/apply/', views.apply_agent, name='apply_agent'),
    path('agent/approve/<int:application_id>/', views.approve_agent, name='approve_agent'),
    path('agent/reject/<int:user_id>/', views.reject_agent, name='reject_agent'),
    path('accounts/login/', CustomLoginView.as_view(), name='login'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('agent/rate/<int:agent_id>/', views.rate_agent, name='rate_agent'),
    path('listings/', views.user_listings, name='user_listings'),
    path('agent/interests/', views.agent_interests, name='agent_interests'),
    # path('search/', views.search_properties, name='search_properties'),
    # Normal User
    path('user/properties/', views.user_properties, name='user_properties'),
    path('user/transactions/', views.user_transactions, name='user_transactions'),
    path('user/interests/', views.user_interests, name='user_interests'),
    # Agent
    path('agent/properties/', views.agent_properties, name='agent_properties'),
    path('agent/transactions/', views.agent_transactions, name='agent_transactions'),
    path('agent/interests/', views.agent_interests, name='agent_interests'),
    # Admin
    path('agent/properties/', views.agent_properties, name='agent_properties'),
    path('property/<int:property_id>/request-transaction/', views.request_transaction, name='request_transaction'),
    path('admin/confirm-transaction/<int:transaction_id>/', views.admin_confirm_transaction, name='admin_confirm_transaction'),
    path('admin/properties/', views.admin_properties, name='admin_properties'),
    path('admin/pending-properties/', views.admin_pending_properties, name='admin_pending_properties'),
    path('admin/agent-requests/', views.admin_agent_requests, name='admin_agent_requests'),
    path('admin/interests/', views.admin_interests, name='admin_interests'),
    path('admin/transactions/', views.admin_transactions, name='admin_transactions'),
    path('admin/', admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)