from amclient import AMClient

# Create a new AMClient object
am = AMClient(ss_url="http://10.10.10.20", ss_user_name="admin", ss_api_key="this_is_the_am_api_key")

# Get the list of all transfer source directories
print(am.list_location_purposes())