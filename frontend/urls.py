from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

from . import views

app_name = 'frontend'
urlpatterns = [
    path('', views.index, name='index'),
    path('home/', views.index, name='index'),
    path('list/', views.IndexView.as_view(), name='list'),
    path('please_register/', views.please_register, name='please_register'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('profile/', views.profile, name='profile'),
    path('accounts/login', views.login, name='login'),

    path('launch/', views.launch, name='launch'),
    path('launch/<int:pk>', views.launch_pk, name='launch_pk'),
    path('details/<int:pk>', views.DetailView.as_view(), name='detail'),

    path('claimed_key_table/', views.claimed_key_table, name='claimed_key_table'),
    path('key_table/<int:pk>', views.key_table, name='key_table'),
    path('info_table/<int:pk>', views.info_table, name='info_table'),
    path('conformer_table/<int:pk>', views.conformer_table, name='conformer_table'),

    path('log/<int:pk>', views.log, name='log'),
    path('submit_calculation/', views.submit_calculation, name='submit_calculation'),
    path('get_structure/', views.get_structure, name='get_structure'),
    path('generate_keys/', views.generate_keys, name='generate_keys'),
    path('claim_key/', views.claim_key, name='claim_key'),
    path('owned_accesses/', views.owned_accesses, name='owned_accesses'),
    path('test_access/', views.test_access, name='test_access'),
    path('get_command_status/', views.get_command_status, name='get_command_status'),

    path('delete_key/', views.delete_key, name='delete_key'),
    path('delete_access/<int:pk>', views.delete_access, name='delete_access'),
    path('download_structure/<int:pk>', views.download_structure, name='download_structure'),
    path('status/<int:pk>', views.status, name='status'),
    path('icon/<int:pk>', views.icon, name='icon'),
    path('uvvis/<int:pk>', views.uvvis, name='uvvis'),
    path('nmr/<int:pk>', views.nmr, name='nmr'),
    path('delete/<int:pk>', views.delete, name='delete'),
    path('manage_access/<int:pk>', views.manage_access, name='manage_access'),
    path('add_clusteraccess/', views.add_clusteraccess, name='add_clusteraccess'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


