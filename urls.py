from django.conf.urls import url
from .views import LawnEngineProcessing, \
    LawnEngineReport, \
    DeleteLawnEngine, \
    InternalLawnParametersRC, \
    InternalLawnParametersRUD, \
    GetLawnParamDefault, \
    CheckWeatherExistence

from .views import BridgeParcelData, ZillowData, WeatherHistory


urlpatterns = [
    # Lawn engine single user fetch , delete and processing
    url(r'^lawnengine/$', LawnEngineProcessing.as_view()),
    # get api to fetch lawn engine data for a particular user
    url(r'^lawnengine/(?P<lawn_id>\d+)/$', LawnEngineReport.as_view()),
    # delete lawn engine data for a particular user.
    url(r'^deletelawnengine/(?P<lawn_id>\d+)/$', DeleteLawnEngine.as_view()),
    # Lawn engine processing according to CSV
    # Fetch lawn engine and Lawn engine testing api
    url(r'^getdefaultparam/$', GetLawnParamDefault.as_view()),
    # Internal Parameter API (CRUD)
    url(r'^internal_parameters/$', InternalLawnParametersRC.as_view()),

    url(r'^internal_parameters/(?P<pk>\d+)/$', InternalLawnParametersRUD.as_view()),

    url(r'^lawnengineproducts/(?P<user_id>\d+)/$', GetAllProducts.as_view()),
    # check existence of weather data.
    url(r'^checkweatherdata/$', CheckWeatherExistence.as_view()),


    # api to list all the users in the system using Zillow API
    url(r'^zillow/$', ZillowData.as_view()),
    # gets weather history for a particular geographic coordinate
    url(r'^weatherhistory/$', WeatherHistory.as_view()),
    # Gets parcel data for bridge.
    url(r'^bridgeparcel/$', BridgeParcelData.as_view()),
]
