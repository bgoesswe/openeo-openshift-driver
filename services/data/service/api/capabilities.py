''' /data route of Data Service '''

from flask import Blueprint
from flask_cors import cross_origin
from service.api.api_utils import parse_response

CAPABILITIES_BLUEPRINT = Blueprint("capabilities", __name__)

@CAPABILITIES_BLUEPRINT.route("/capabilities", methods=["GET"])
@cross_origin(origins="*", supports_credentials=False, methods="GET")
def get_capabilities():
    ''' Get data records from PyCSW server '''

    capabilities = [
        "/capabilities",
        "/capabilities/output_formats",
        "/capabilities/services",
        "/data",
        "/data/{product_id}",
        "/processes",
        "/processes/{process_id}",
        "/auth/login",
        "/jobs",
        "/jobs/{job_id}",
        "/jobs/{job_id}/download"
    ]

    return parse_response(200, data=capabilities)

@CAPABILITIES_BLUEPRINT.route("/capabilities/output_formats", methods=["GET"])
@cross_origin(origins="*", supports_credentials=False, methods="GET")
def get_output_formats():
    ''' Get data records from PyCSW server '''
    
    output_formats = {
        "default": "GTiff",
        "formats": {
            "GTiff": {
                "tiled": "By default [false] stripped TIFF files are created. This option can be used to force creation of tiled TIFF files [true].",
                "compress": "Set the compression [JPEG/LZW/DEFLATE/NONE] to use.",
                "photometric": "Set the photometric interpretation tag [MINISBLACK/MINISWHITE/RGB/CMYK/YCBCR/CIELAB/ICCLAB/ITULAB].",
                "jpeg_quality": "Set the JPEG quality [1-100] when using JPEG compression. Default: 75"
            },
            "PNG": {
                "worldfile": "Force the generation of an associated ESRI world file."
            }
        }
    }

    return parse_response(200, data=output_formats)

@CAPABILITIES_BLUEPRINT.route("/capabilities/services", methods=["GET"])
@cross_origin(origins="*", supports_credentials=False, methods="GET")
def get_services():
    ''' Get data records from PyCSW server '''
    
    services = []

    return parse_response(200, data=services)