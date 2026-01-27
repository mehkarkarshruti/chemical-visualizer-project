from django.urls import path
from .views import UploadCSV, SummaryView

urlpatterns = [
    path('upload/', UploadCSV.as_view(), name='upload-csv'),
    path('summary/', SummaryView.as_view(), name='summary'),
]