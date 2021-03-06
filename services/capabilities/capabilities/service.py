""" Capabilities Discovery """
import ast
import logging
from os import environ
from typing import Optional

from nameko.rpc import rpc

service_name = "capabilities"
LOGGER = logging.getLogger('standardlog')


class ServiceException(Exception):
    """ServiceException raises if an exception occured while processing the
    request. The ServiceException is mapping any exception to a serializable
    format for the API gateway.
    """

    def __init__(self, service: str, code: int, user_id: Optional[str], msg: str, internal: bool = True,
                 links: list = None) -> None:
        if not links:
            links = []
        self._service = service
        self._code = code
        self._user_id = user_id
        self._msg = msg
        self._internal = internal
        self._links = links
        LOGGER.exception(msg, exc_info=True)

    def to_dict(self) -> dict:
        """Serializes the object to a dict.

        Returns:
            dict -- The serialized exception
        """
        return {
            "status": "error",
            "service": self._service,
            "code": self._code,
            "user_id": self._user_id,
            "msg": self._msg,
            "internal": self._internal,
            "links": self._links
        }


class CapabilitiesService:
    """Discovery of capabilities that are available at the back-end.
    """

    name = service_name

    @rpc
    def send_index(self, api_spec: dict, user_id: str = None) -> dict:
        """The function returns a JSON object containing the available routes and
        HTTP methods as defined in the OpenAPI specification.

        Arguments:
            api_spec {dict} -- OpenAPI Specification

        Keyword Arguments:
            user_id {str} -- User Id (not needed, exists for compatibility reasons)

        Returns:
            Dict -- JSON object contains the API capabilities
        """
        # TODO: Implement billing plans

        try:
            endpoints = []
            # Remove /.well-known/openeo endpoint, must not be listed under versioned URLs
            if './well-known/openeo' in api_spec['paths']:
                _ = api_spec['paths'].pop('/.well-known/openeo')
            for path_name, methods in api_spec["paths"].items():
                path_to_replace = path_name[path_name.find(':'):path_name.find('}')]
                path_name = path_name.replace(path_to_replace, '')
                endpoint = {"path": path_name, "methods": []}
                for method_name, _ in methods.items():
                    if method_name in ("get", "post", "patch", "put", "delete"):
                        endpoint["methods"].append(method_name.upper())
                endpoints.append(endpoint)

            capabilities = {
                "api_version": api_spec["info"]["version"],
                "backend_version": api_spec["info"]["backend_version"],
                "title": api_spec["info"]["title"],
                "description": api_spec["info"]["description"],
                "endpoints": endpoints,
                "stac_version": api_spec["info"]["stac_version"],
                "id": api_spec["info"]["id"],
                "links": [],  # TODO add links
                "production": api_spec["info"]["production"],
            }

            return {
                "status": "success",
                "code": 200,
                "data": capabilities,
            }

        except Exception as exp:
            return ServiceException(CapabilitiesService.name, 500, user_id, str(exp)).to_dict()

    @rpc
    def get_versions(self, api_spec: dict, user_id: str = None) -> dict:
        """Lists OpenEO API versions available at the back-end.

        Arguments:
            api_spec {dict} -- OpenAPI Specification

        Keyword Arguments:
            user_id {str} -- User Id (not needed, exists for compatibility reasons)

        Returns:
            Dict -- Contains the supported OpenEO API versions
        """
        try:
            # NB The api 'versions' must match exactly the version numbers available here:
            # https://github.com/Open-EO/openeo-api
            api_versions = []
            for ver in api_spec["servers"]["versions"]:
                this_ver = api_spec["servers"]["versions"][ver]
                this_ver["production"] = api_spec["info"]["production"]
                if ast.literal_eval(environ['DEVELOPMENT']):
                    # change https url to localhost
                    this_ver['url'] = environ['GATEWAY_URL'] + this_ver['url'].split(".eu")[1]
                api_versions.append(this_ver)

            return {
                "status": "success",
                "code": 200,
                "data": {
                    "versions": api_versions
                }
            }

        except Exception as exp:
            return ServiceException(CapabilitiesService.name, 500, user_id, str(exp)).to_dict()

    @rpc
    def get_file_formats(self, api_spec: dict, user_id: str = None) -> dict:
        """Lists input / output formats available at the back-end.

        Arguments:
            api_spec {dict} -- OpenAPI Specification

        Keyword Arguments:
            user_id {str} -- User Id (not needed, exists for compatibility reasons)

        Returns:
            Dict -- Describes all supported input / output formats
        """
        def get_dict(file_fmts: dict) -> dict:
            final_fmt = {}
            for fmt in file_fmts:
                final_fmt[fmt["name"]] = {
                    "title": fmt.get("title", None),
                    "gis_data_types": fmt["gis_data_types"],
                    "parameters": fmt.get("parameters", {})
                }
            return final_fmt

        try:
            file_formats = api_spec["info"]["file_formats"]

            return {
                "status": "success",
                "code": 200,
                "data": {
                    "output": get_dict(file_formats["output"]),
                    "input": get_dict(file_formats["input"]),
                },
            }
        except Exception as exp:
            return ServiceException(CapabilitiesService.name, 500, user_id, str(exp)).to_dict()

    @rpc
    def get_udfs(self, api_spec: dict, user_id: str = None) -> dict:
        """Lists UDFs available at the back-end.

        Arguments:
            api_spec {dict} -- OpenAPI Specification

        Keyword Arguments:
            user_id {str} -- User Id (not needed, exists for compatibility reasons)

        Returns:
            Dict -- Contains detailed description about the supported UDF runtimes
        """
        try:
            udf_all = api_spec["info"]["udf"]

            return {
                "status": "success",
                "code": 200,
                "data": udf_all,
            }
        except Exception as exp:
            return ServiceException(CapabilitiesService.name, 500, user_id, str(exp)).to_dict()

    @rpc
    def get_service_types(self, api_spec: dict, user_id: str = None) -> dict:
        """Lists service types available at the back-end.

        Arguments:
            api_spec {dict} -- OpenAPI Specification

        Keyword Arguments:
            user_id {str} -- User Id (not needed, exists for compatibility reasons)

        Returns:
            Dict -- Contains supported secondary services
        """
        try:

            return {
                "status": "success",
                "code": 200,
                "data": {'Secondary services': 'None implemented.'},
            }
        except Exception as exp:
            return ServiceException(CapabilitiesService.name, 500, user_id, str(exp)).to_dict()
