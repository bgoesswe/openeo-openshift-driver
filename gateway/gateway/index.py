""" / """
from flask_restful_swagger_2 import swagger, Resource
from flask_restful.utils import cors
from requests import get

from . import rpc
from .src.response import *
from .src.cors import CORS

from flask import redirect
from flask_restful import Resource


class Index(Resource):
    __res_parser = ResponseParser()

    @cors.crossdomain(
        origin=["*"], 
        methods=["GET"],
        headers=["Content-Type"])
    @swagger.doc(CORS().__parse__())
    def options(self):
        return self.__res_parser.code(200)

    @cors.crossdomain(
        origin=["*"], 
        methods=["GET"],
        headers=["Content-Type"])
    @swagger.doc({
        "tags": ["Capabilities"],
        "description": "Returns the capabilities, i.e., which OpenEO API features are supported by the back-end.",
        "responses": {
            "200": OK("An array of implemented API endpoints.").__parse__(),
            "503": ServiceUnavailable().__parse__()
        }
    })
    def get(self):
        return redirect("/capabilities")


class Capabilities(Resource):
    __res_parser = ResponseParser()

    @cors.crossdomain(
        origin=["*"], 
        methods=["GET"],
        headers=["Content-Type"])
    @swagger.doc(CORS().__parse__())
    def options(self):
        return self.__res_parser.code(200)

    @cors.crossdomain(
        origin=["*"], 
        methods=["GET"],
        headers=["Content-Type"])
    @swagger.doc({
        "tags": ["Capabilities"],
        "description": "Returns the capabilities, i.e., which OpenEO API features are supported by the back-end.",
        "responses": {
            "200": OK("An array of implemented API endpoints.").__parse__(),
            "503": ServiceUnavailable().__parse__()
        }
    })
    def get(self):
        capabilities = [
            "/capabilities",
            "/capabilities/output_formats",
            "/auth/register",
            "/auth/login",
            "/data",
            "/data/<string:product_id>",
            "/processes",
            "/processes/<string:process_id>",
            "/jobs",
            "/jobs/<string:job_id>",
            "/jobs/<string:job_id>/queue",
            "/jobs/<string:job_id>/download",
            "/download/<string:job_id>/<string:file_name>"
        ]

        return self.__res_parser.data(200, capabilities)

class OutputFormats(Resource):
    __res_parser = ResponseParser()

    @cors.crossdomain(
        origin=["*"], 
        methods=["GET"],
        headers=["Content-Type"])
    @swagger.doc(CORS().__parse__())
    def options(self):
        return self.__res_parser.code(200)

    @cors.crossdomain(
        origin=["*"], 
        methods=["GET"],
        headers=["Content-Type"])
    @swagger.doc({
        "tags": ["Capabilities"],
        "description": "The request will ask the back-end for supported output formats, e.g. PNG, GTiff and time series, and its default output format.",
        "responses": {
            "200": OK("An object with the default output format and a map containing all output formats as keys and an object that defines available options.").__parse__(),
            "503": ServiceUnavailable().__parse__()
        }
    })
    def get(self):
        output_formats = {
            "default": "GTiff",
            "formats": {
                "GTiff": {
                    "tiled": "By default [false] stripped TIFF files are created. This option can be used to force creation of tiled TIFF files [true].",
                    "compress": "Set the compression [JPEG/LZW/DEFLATE/NONE] to use.",
                    "photometric": "Set the photometric interpretation tag [MINISBLACK/MINISWHITE/RGB/CMYK/YCBCR/CIELAB/ICCLAB/ITULAB].",
                    "jpeg_quality": "Set the JPEG quality [1-100] when using JPEG compression. Default: 75"
                }
            }
        }

        return self.__res_parser.data(200, output_formats)