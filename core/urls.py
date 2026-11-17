from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

urlpatterns = [
    path('', views.home, name='home'),
    path(
        'login/',
        auth_views.LoginView.as_view(
            authentication_form=LoginForm,
            redirect_authenticated_user=True,
        ),
        name='login',
    ),
    path('signup/', views.signup, name='signup'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),

    path('users/', views.user_list, name='user_list'),
    path('users/add/', views.user_add, name='user_add'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),

    path('machines/', views.machine_list, name='machine_list'),
    path('machines/add/', views.machine_add, name='machine_add'),
    path('machines/<int:pk>/edit/', views.machine_edit, name='machine_edit'),
    path('machines/<int:pk>/delete/', views.machine_delete, name='machine_delete'),

    path('breakdowns/', views.breakdown_list, name='breakdown_list'),
    path('breakdowns/add/', views.breakdown_add, name='breakdown_add'),
    path('breakdowns/<int:pk>/edit/', views.breakdown_edit, name='breakdown_edit'),
    path('breakdowns/<int:pk>/delete/', views.breakdown_delete, name='breakdown_delete'),

    path('interventions/', views.intervention_list, name='intervention_list'),
    path('interventions/add/', views.intervention_add, name='intervention_add'),
    path('interventions/<int:pk>/', views.intervention_detail, name='intervention_detail'),
    path('interventions/<int:pk>/edit/', views.intervention_edit, name='intervention_edit'),
    path('interventions/<int:pk>/update/', views.intervention_update, name='intervention_update'),
    path('interventions/<int:pk>/delete/', views.intervention_delete, name='intervention_delete'),
]
