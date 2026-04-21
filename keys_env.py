import os

rollbar_access_token = os.getenv('SECRET_ROLLBAR_ACCESS_TOKEN', 'test')

#get your individual key from here: https://developer.nrel.gov/docs/api-key/ and replace the DEMO_KEY with that
pvwatts_api_key = os.getenv('SECRET_PVWATTS_NLR_API_KEY', os.getenv('NLR_API_KEY', 'DEMO_KEY'))
developer_nrel_gov_key = os.getenv('SECRET_DEVELOPER_NLR_GOV_API_KEY', os.getenv('NLR_API_KEY', 'DEMO_KEY'))
ashrae_tmy_key = os.getenv('SECRET_ASHRAE_TMY_NLR_API_KEY', os.getenv('NLR_API_KEY', 'DEMO_KEY'))


secret_key_ = os.getenv('SECRET_DJANGO_SECRET_KEY', 'secret_key_test')

db_host = os.getenv('DB_HOST', os.getenv('SECRET_DB_HOST', 'localhost'))
db_name = os.getenv('DB_NAME', os.getenv('SECRET_DB_NAME', 'reopt'))
db_username = os.getenv('DB_USERNAME', os.getenv('SECRET_DB_USERNAME', 'reopt_api'))
db_password = os.getenv('DB_PASSWORD', os.getenv('SECRET_DB_PASSWORD', 'reopt'))
db_search_path = os.getenv('DB_SEARCH_PATH', os.getenv('SECRET_DB_SEARCH_PATH', 'reopt_api'))
redis_host = os.getenv('REDIS_HOST', os.getenv('SECRET_REDIS_HOST', 'localhost'))
redis_password = os.getenv('REDIS_PASSWORD', os.getenv('SECRET_REDIS_PASSWORD', 'password'))
