from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('', views.index, name='index'),
    path('deposit/', views.deposit, name='deposit'),
    path('loan/request/', views.request_loan, name='request_loan'),
    # --- NEW ADMIN ROUTES ---
    path('admin-panel/', views.admin_dashboard, name='admin_dashboard'),
    path('loan/repay/', views.repay_loan, name='repay_loan'),
    path('loan/<int:loan_id>/<str:action>/', views.process_loan, name='process_loan'),
    path('join/', views.join_chama, name='join_chama')
    
]