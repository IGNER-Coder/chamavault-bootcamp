from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.index, name='index'),
    path('deposit/', views.deposit, name='deposit'),
    path('loan/request/', views.request_loan, name='request_loan'),
    path('create-group/', views.create_group, name='create_group'),
    # --- NEW ADMIN ROUTES ---
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/settings/', views.group_settings, name='group_settings'),
    path('pricing/', views.pricing, name='pricing'),
    path('about/', views.about, name='about'),
    path('statement/download/', views.download_statement, name='download_statement'),
    path('loan/repay/', views.repay_loan, name='repay_loan'),
    path('loan/<int:loan_id>/<str:action>/', views.process_loan, name='process_loan'),
    path('api/v1/c2b/callback', views.mpesa_callback, name='mpesa_callback'),
    path('join/', views.join_chama, name='join_chama'),
    path('statement/download/', views.download_statement, name='download_statement')
    
    
    
]