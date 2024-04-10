from pprint import pprint
from amclient import AMClient
from sam_client import SAMClient

# Create a new AMClient object
am = AMClient(ss_url="http://10.10.10.20:8000", ss_user_name="admin", ss_api_key="this_is_the_ss_api_key")
am.am_url = "http://10.10.10.20"
am.am_user_name = "admin"
am.am_api_key = "this_is_the_am_api_key"

# Create a new SAMClient object
sam = SAMClient(am_url="http://10.10.10.20")
sam.setup_login("admin", "this_is_the_am_api_key")
sam.ss_setup_login("admin", "this_is_the_ss_api_key")

"""
# Upload file
response = am.create_package()
print(response)
print(type(response))
print()

transfer_id = response["id"]
print("Transfer ID: " + transfer_id)
am.transfer_uuid = transfer_id
print(am.get_transfer_status())

# Create package
transfer_id = sam.create_package("vagrant/main/test")["id"]
sip_uuid = sam.get_sip_from_transfer(transfer_id)
print(sip_uuid)
dip_uuid = sam.get_dip_from_sip(sip_uuid)
print(dip_uuid)
"""

# List completed transfers
assert am.completed_transfers() == sam.completed_transfers()

pprint(sam.get_all_packages())
assert am.get_all_packages(params={}) == sam.get_all_packages()
package_uuid = "f01707f9-8e76-490a-9e16-e7b361a002ee"
am.package_uuid = package_uuid
assert am.get_package_details() == sam.get_package_details(package_uuid)

# Download package (must use AIP/DIP UUID from Storage Service)
download_uuid = "f01707f9-8e76-490a-9e16-e7b361a002ee"
assert am.download_package(download_uuid) == sam.download_package(download_uuid)
