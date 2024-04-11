import os
from pprint import pprint
from typing import no_type_check
import amclient
from time import sleep


class SAMClient:

    @no_type_check
    def __init__(self, am_url: str, ss_url: str | None = None):
        """
        Initializes the SAMClient object with the given Archivematica URL.

        Also sets the Storage Service URL if provided, otherwise defaults to the am_url + :8000.
        """
        self.super = amclient.AMClient()
        self.super.am_url = am_url
        self.super.ss_url = ss_url if ss_url else am_url + ":8000"

    @no_type_check
    def setup_login(self, user_name: str, api_key: str) -> "SAMClient":
        """Sets up the login credentials for Archivematica requests."""
        self.super.am_user_name = user_name
        self.super.am_api_key = api_key
        return self

    @no_type_check
    def ss_setup_login(self, ss_user_name: str, ss_api_key: str) -> "SAMClient":
        """Sets up the login credentials for Storage Service requests."""
        self.super.ss_user_name = ss_user_name
        self.super.ss_api_key = ss_api_key
        return self

    @no_type_check
    def create_package(
        self,
        transfer_directory: str,
        transfer_name: str | None = None,
        transfer_type: str = "standard",
        pipeline: str = "automated",
    ) -> dict:
        """
        Creates a new package in Archivematica.

        Uploads the given transfer directory, under the transfer name, using the given pipeline.
        """
        self.super.transfer_directory = transfer_directory
        if transfer_name is None:
            transfer_name = os.path.basename(transfer_directory)
        self.super.transfer_name = transfer_name
        self.super.transfer_type = transfer_type
        self.super.processing_config = pipeline
        return self.super.create_package()

    @no_type_check
    def get_transfer_status(self, id: str) -> dict:
        """Returns the status of the current transfer."""
        self.super.transfer_uuid = id
        return self.super.get_transfer_status()

    @no_type_check
    def completed_transfers(self) -> dict:
        """Returns a list of completed transfers."""
        return self.super.completed_transfers()

    @no_type_check
    def get_all_packages(self) -> dict:
        """Returns a list of all packages in the Storage System."""
        return self.super.get_all_packages(params={})

    @no_type_check
    def get_package_details(self, package_uuid: str) -> dict:
        """Returns the details of the given package."""
        self.super.package_uuid = package_uuid
        return self.super.get_package_details()

    @no_type_check
    def download_package(self, package_uuid: str, save_dir: str | None = None) -> str:
        """Downloads the given package from the Storage Service.

        Saves the package to the given directory, or the current working directory if not provided.

        Returns the filename of the downloaded package.
        """
        current_path = os.getcwd()
        if save_dir is not None:
            os.chdir(save_dir)
        filename = self.super.download_package(package_uuid)
        os.chdir(current_path)
        return filename

    @no_type_check
    def get_sip_from_transfer(self, transfer_uuid: str, timeout: int = 60) -> str:
        """Waits until transfer has been processed and returns the SIP UUID."""
        pprint(self.get_transfer_status(transfer_uuid))
        response = 0
        while type(response) is int and timeout > 0:
            response = self.get_transfer_status(transfer_uuid)
            sleep(1)
            timeout -= 1
            print("Waiting for processing to begin...")
        while response.get("sip_uuid", None) is None and timeout > 0:
            response = self.get_transfer_status(transfer_uuid)
            timeout -= 1
            sleep(1)
            print("Waiting for SIP to be created...")
        return response["sip_uuid"]

    @no_type_check
    def get_dip_from_sip(self, sip_uuid: str, timeout: int = 60) -> str:
        """Waits until the SIP has been processed and gives the related DIP UUID."""
        response = 0
        while type(response) is int and timeout > 0:
            response = self.get_package_details(sip_uuid)
            timeout -= 1
            sleep(1)
            print("Waiting for processing to begin...")
        while response.get("related_packages", None) is None and timeout > 0:
            response = self.get_package_details(sip_uuid)
            timeout -= 1
            sleep(1)
            print("Waiting for DIP to be created...")
        package = response["related_packages"][0]
        if self.get_package_type(package) == "DIP":
            return package["uuid"]
        raise Exception("No DIP found in SIP.")

    @no_type_check
    def get_package_type(self, package_uuid: str) -> str:
        """Returns the type of the given package."""
        return self.get_package_details(package_uuid)["package_type"]
