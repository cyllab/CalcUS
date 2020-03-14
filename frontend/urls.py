from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'frontend'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('home/', views.IndexView.as_view(), name='index'),
    path('launch/', views.launch, name='launch'),
    path('submit_calculation/', views.submit_calculation, name='submit_calculation'),
    path('get_structure/', views.get_structure, name='get_structure'),
    path('download_structure/<int:pk>', views.download_structure, name='download_structure'),
    path('delete/<int:pk>', views.delete, name='delete'),
    path('conformer_table/<int:pk>', views.conformer_table, name='conformer_table'),
    path('home/<int:page>', views.IndexView.as_view(), name='index'),
    path('details/<int:pk>', views.DetailView.as_view(), name='detail'),
    path('please_register/', views.please_register, name='please_register'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile, name='profile'),
    path('accounts/login', views.login, name='login'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


