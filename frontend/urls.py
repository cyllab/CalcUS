from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'frontend'
urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.index, name='index'),
    #path('home/<int:page>', views.index, name='index'),
    path('list/', views.IndexView.as_view(), name='list'),
    path('launch/', views.launch, name='launch'),
    path('submit_calculation/', views.submit_calculation, name='submit_calculation'),
    path('get_structure/', views.get_structure, name='get_structure'),
    path('download_structure/<int:pk>', views.download_structure, name='download_structure'),
    path('info_table/<int:pk>', views.info_table, name='info_table'),
    path('status/<int:pk>', views.status, name='status'),
    path('icon/<int:pk>', views.icon, name='icon'),
    path('uvvis/<int:pk>', views.uvvis, name='uvvis'),
    path('nmr/<int:pk>', views.nmr, name='nmr'),
    path('delete/<int:pk>', views.delete, name='delete'),
    path('conformer_table/<int:pk>', views.conformer_table, name='conformer_table'),
    path('details/<int:pk>', views.DetailView.as_view(), name='detail'),
    path('please_register/', views.please_register, name='please_register'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile, name='profile'),
    path('accounts/login', views.login, name='login'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


