"""
views module to handle the logics of the APIs.

"""

from datetime import datetime, date
from rest_framework import generics, permissions, status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.request import Request
from analytic.models import SoilInfo, SoilTest
from lawn.models import Lawn
from .serializers import InternalParameterSerializer
from ..models import DateAndPouches, LawnEngine, GrassPotential, InternalParameters
from .functions import get_precip, data_saving, main_lawn_engine, \
    lawn_engine_processing_from_csv, fetch_internal_parameters, fetch_internal_param_default_value, \
    date_to_vector_date_for_lawn_engine, fetch_pouches_per_app_and_pouches, get_temp_and_precip_from_database, \
    update_start_date_for_le_use
from django.utils import timezone
from lawn.models import Lawn, LawnInfo
from orderproduct.models import Orderproduct
from account.api.tasks import background_lawn_engine_csv_processing
from calendar import month_name
from .lawn_engine.engine.main import Manager
from .lawn_engine.test_main import get_prior_apps
import logging
import json
from lawn_care.permissions import IsAdminOrAuthenticatedReadOnly


class LawnEngineProcessing(APIView):
    """Lawn engine api post and method
       Takes : lawn_id and start date as body parameters
       to return grass potential, stress zone and apps
    """
    permission_classes = (permissions.IsAuthenticated, )

    def post(self, request):
        """Post method for lawn_engine api.
        Works 2 ways
        1. If soil data is absent gets prior pouches from lawn engine module and saves it with other data.
        2. If soil data is there then it takes pouches and soil data and calculate lawn engine data using them.
        Works around run type. If first run ignores soil data else process using it if it exist

        Args:
            request
            request.lawn_id
            request.start_date

        Returns:
            saves lawn engine processed data to database.

        """
        try:
            lawn_pk = request.data['lawn_id']
            lawn = Lawn.objects.get(pk=lawn_pk)
        except KeyError:
            raise ValidationError(detail={'detail': 'lawn_id is required'})
        except ValueError:
            raise ValidationError(detail={'detail': 'lawn_id must be valid integer'})
        except Lawn.DoesNotExist:
            raise NotFound(detail=f'Lawn does not exist for lawn_id: {lawn_pk}')

        user_input = request.data.get('user_input', [])
        subscription_year = date.today().year

        try:
            start_date_str = request.data.get('start_date')
            if not start_date_str:
                start_date_str = str(timezone.now())[:10]
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            start_date = update_start_date_for_le_use(start_date)
        except Exception as e:
            print(e)
            return Response("Failed because of wrong date format or date.", status.HTTP_200_OK)
        result = main_lawn_engine(lawn_pk, start_date, user_input, subscription_year)
        return Response(result, status.HTTP_200_OK)


class LawnEngineReport(APIView):
    """ Fetches lawn engine result for a particular user based on lawn id
        Return: grass potential, date and pouches & lawn engine data
    """
    permission_classes = [IsAdminOrAuthenticatedReadOnly]

    def get(self, _request: Request, lawn_id):
        """Fetches lawn engine result for a particular user based on lawn id.

        Args:
            _request
            lawn_id(int).

        Return:
             grass potential, date and pouches & lawn engine data.

        """
        try:
            queryset = LawnEngine.objects.filter(lawn_id=lawn_id)
            lawn_data = Lawn.objects.get(pk=lawn_id)
            lawnengine = {}
            for lawn_engine in queryset:
                lawnengine['lawn_id'] = lawn_engine.lawn_id
                lawnengine['start_date'] = lawn_engine.start_date
                lawnengine['user_input'] = lawn_engine.user_input
                lawnengine['stress_zone'] = lawn_engine.stress_zone
                lawnengine['grass_type'] = lawn_engine.grass_type
                lawnengine['run_type'] = lawn_engine.run_type
                lawnengine['task_status'] = lawn_engine.task_status
                lawnengine['updated_at'] = lawn_engine.updated_at
                lawnengine['max_lawn_size'] = lawn_engine.max_lawn_size
                lawnengine['pouches_per_app'] = lawn_engine.pouches_per_app
                lawnengine['soil_update_date'] = ""
                lawnengine['lawn_update_date'] = ""
                lawnengine['address'] = ""
                lawnengine['grass_potential'] = []
                lawnengine['date_and_pouches'] = []
                try:
                    lawninfo = LawnInfo.objects.filter(lawn=lawn_id)
                    lawnengine['lawn_update_date'] = lawninfo[0].updated_at
                except Exception as e:
                    logging.exception(e)
                try:
                    for soil in SoilInfo.objects.filter(lawn=lawn_data.id):
                        for soiltest in SoilTest.objects.filter(soilinfo=soil.id):
                            lawnengine['soil_update_date'] = soiltest.date_tested
                except Exception as e:
                    logging.exception(e)
                for grass_data in GrassPotential.objects.filter(lawn_engine=lawn_engine.id).order_by("id"):
                    grassdata = {}
                    grassdata['date'] = grass_data.date
                    grassdata['value'] = grass_data.value
                    lawnengine['grass_potential'].append(grassdata)
                for dateandpouches in DateAndPouches.objects.filter(lawn_engine=lawn_engine.id).order_by("id"):
                    date_and_pouches = {}
                    date_and_pouches['date'] = dateandpouches.date
                    date_and_pouches['pouches'] = dateandpouches.pouches
                    lawnengine['date_and_pouches'].append(date_and_pouches)
                for address in Lawn.objects.filter(id=lawn_engine.lawn_id):
                    lawnengine['address'] = address.address
            return Response(lawnengine, status.HTTP_200_OK)
        except Exception as e:
            logging.exception(e)
            return Response("Not Found", status.HTTP_404_NOT_FOUND)


class DeleteLawnEngine(APIView):
    """This is meant for testing and only for testing(Do not use). Function to delete the current lawn_engine data"""
    permission_classes = [IsAdminOrAuthenticatedReadOnly]

    def get(self, _request: Request, lawn_id):
        """Back end get api for deleting specific user's lawn engine data.

        Args :
            _request
            lawn_id(int)

        Returns:
             deleted data for that lawn id.

        """
        LawnEngine.objects.filter(lawn_id=lawn_id).delete()
        return Response("done", status.HTTP_200_OK)


class InternalLawnParametersRC(generics.ListCreateAPIView):
    """Internal Lawn Parameters is meant to read internal lawn api parameters used for lawn engine processing also save
    and update them in DB.

    Methods : Post, Get.

    """
    permission_classes = [IsAdminOrAuthenticatedReadOnly]
    queryset = InternalParameters.objects.filter(is_delete=False)
    serializer_class = InternalParameterSerializer


class InternalLawnParametersRUD(generics.RetrieveUpdateDestroyAPIView):
    """Internal Lawn Parameters is meant to read internal lawn api parameters used for lawn engine processing also save
    and update them in DB.

    Methods : Post, Get, Update.

    """
    permission_classes = [IsAdminOrAuthenticatedReadOnly]
    queryset = InternalParameters.objects.filter(is_delete=False)
    serializer_class = InternalParameterSerializer


class GetLawnParamDefault(APIView):
    """API to check what Default value of parameters are """
    permission_classes = [IsAdminOrAuthenticatedReadOnly]

    def get(self, _request: Request):
        """Get Api to fetch all data"""
        all_params = fetch_internal_param_default_value()
        return Response(all_params)


class CheckWeatherExistence(APIView):
    """ API to check whether or not the weather data exists for a given lawn """
    permission_classes = [(permissions.IsAuthenticated)]

    def post(self, request):
        """ POST endpoint that takes a provided lawn ID
            and determines if weather data exists for the lawn
        """
        try:
            lawn_id = request.data['lawn_id']
            if Lawn.objects.filter(id=lawn_id).exists():
                weather_data_stored_in_db = get_temp_and_precip_from_database(lawn_id)
            else:
                return Response("Lawn Not Found", status.HTTP_404_NOT_FOUND)
        except KeyError:
            return Response("Lawn ID not provided", status.HTTP_400_BAD_REQUEST)

        if weather_data_stored_in_db == "Failed to fetch weather data":
            return Response(False, status.HTTP_200_OK)
        else:
            return Response(True, status.HTTP_200_OK)


class ZillowData(APIView):
    """
    View to list all users in the system.

    * Requires token authentication.
    * Only admin users are able to access this view.
    """
    # authentication_classes = (authentication.TokenAuthentication,)
    # permission_classes = (permissions.IsAdminUser,)
    # throttle based on ip
    ratelimit_key = 'ip'
    # 50 requests per hour
    ratelimit_rate = '50/h'
    ratelimit_block = True

    def get(self, request):
        """
        Return a list of all users.
        """
        # usernames = [user.username for user in User.objects.all()]
        return Response({})

    def post(self, request):
        # api-endpoint
        zwsid = "zws-id=" + settings.ZILLOW_API_KEY + "&"
        address = "address=" + request.data['address'] + "&"
        citystatezip = "citystatezip=" + request.data['citystatezip']
        URL = settings.ZILOW_URL + \
            zwsid + \
            address + \
            citystatezip
        # urllink = urllib2.urlopen(URL).read()
        # sending get request and saving the response as response object
        r = requests.get(url=URL)
        jsonString = json.dumps(xmltodict.parse(r.content))
        # jsonString.replace("\",' ')
        if jsonString:
            return Response(jsonString)
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)
        return Response(jsonString)


class WeatherHistory(APIView):
    """Weather information"""
    # throttle based on ip
    ratelimit_key = 'ip'
    # 50 requests per hours
    ratelimit_rate = '50/h'
    ratelimit_block = True

    def post(self, request):
        if request.data:
            longitude = request.data['longitude']
            latitude = request.data['latitude']
            # get weather history
            # Weather history analysis: Precipitation ,Min Temp, Max Temp, Cloud info, Avg Temp
            result, array = weatherHistory(longitude, latitude)

        if result:
            return Response(result, status.HTTP_200_OK)
        else:
            return Response({}, status=status.HTTP_400_BAD_REQUEST)


def clean_parcel_address(address):
    """
    cleans out the parcel address for display purposes
    """
    for country_code in ['USA', 'US']:
        if address.endswith(country_code):
            address = address[:-len(country_code)]
    return address.replace(',', '').strip()


class BridgeParcelData(APIView):
    """
    get:
    accepts address.full URL param containing full string address and returns parcel data
    """
    permission_classes = [(ValidKey)]

    def get(self, request):
        address = request.GET.get('address')
        if not address:
            raise ParseError(detail='address param is required')
        address = clean_parcel_address(address)
        params = {
            'access_token': settings.BRIDGE_API_KEY,
            'limit': 1,
            'address.full': address
        }
        try:
            response = requests.get(url=settings.BRIDGE_URL, params=params)
        # Log error message and return ServiceUnavailable if request to BridgeAPI fails
        except requests.exceptions.ConnectionError:
            capture_message("BridgeAPI ConnectionError", level="error")
            raise ServiceUnavailable(detail='parcel data service unavailable')
        if response.status_code == 200:
            parcel_data = response.json()['bundle'][0]
            return Response({'parcel_data': parcel_data})
        # Log error message and return ServiceUnavailable if api token is rejected
        if response.status_code == 403:
            capture_message("BridgeAPI 403 Unauthorized", level="error")
            raise ServiceUnavailable(detail='parcel data service unavailable')
        # Log unknown error and return ServiceUnavailable (possible ratelimit)
        capture_message("BridgeAPI unknown error", level="error")
        raise ServiceUnavailable(detail='parcel data service unavailable')

