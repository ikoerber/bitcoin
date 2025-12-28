"""
URL configuration for charts app
"""

from django.urls import path
from . import views

app_name = 'charts'

urlpatterns = [
    # Frontend
    path('', views.dashboard, name='dashboard'),

    # REST API Endpoints
    path('api/ohlcv/<str:timeframe>/', views.OHLCVDataView.as_view(), name='ohlcv'),
    path('api/latest-price/<str:timeframe>/', views.LatestPriceView.as_view(), name='latest-price'),
    path('api/indicators/<str:timeframe>/', views.IndicatorsView.as_view(), name='indicators'),
    path('api/gaps/<str:timeframe>/', views.GapsView.as_view(), name='gaps'),
    path('api/orderblocks/<str:timeframe>/', views.OrderblocksView.as_view(), name='orderblocks'),
    path('api/summary/', views.DataSummaryView.as_view(), name='summary'),
    path('api/update-database/', views.UpdateDatabaseView.as_view(), name='update-database'),
]
