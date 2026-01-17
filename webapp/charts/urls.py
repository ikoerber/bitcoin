"""
URL configuration for charts app
"""

from django.urls import path
from . import views

app_name = 'charts'

urlpatterns = [
    # Frontend
    path('', views.dashboard, name='dashboard'),
    path('cashflow/', views.cashflow, name='cashflow'),
    path('balance-history/', views.balance_history, name='balance-history'),

    # REST API Endpoints
    path('api/ohlcv/<str:timeframe>/', views.OHLCVDataView.as_view(), name='ohlcv'),
    path('api/latest-price/<str:timeframe>/', views.LatestPriceView.as_view(), name='latest-price'),
    path('api/indicators/<str:timeframe>/', views.IndicatorsView.as_view(), name='indicators'),
    path('api/engulfing/<str:timeframe>/', views.EngulfingPatternsView.as_view(), name='engulfing'),
    path('api/summary/', views.DataSummaryView.as_view(), name='summary'),
    path('api/update-database/', views.UpdateDatabaseView.as_view(), name='update-database'),
    path('api/trading-performance/', views.TradingPerformanceView.as_view(), name='trading-performance'),
    path('api/sync-trades/', views.SyncTradesView.as_view(), name='sync-trades'),
    path('api/sync-asset-history/', views.SyncAssetHistoryView.as_view(), name='sync-asset-history'),
    path('api/sync-open-orders/', views.SyncOpenOrdersView.as_view(), name='sync-open-orders'),
    path('api/account-balance/', views.AccountBalanceView.as_view(), name='account-balance'),
    path('api/cashflow/', views.CashflowView.as_view(), name='cashflow'),
    path('api/balance-history/', views.BalanceHistoryView.as_view(), name='balance-history'),
    path('api/auto-update-status/', views.AutoUpdateStatusView.as_view(), name='auto-update-status'),
]
