""" Query Handler """

#from .models import Query
from hashlib import sha256

#TODO: Move to own file...

EXAMPLE_GRAPH = {
    "process_id": "min_time",
    "process_description": "Deriving minimum NDVI measurements over pixel time series of Sentinel 2 imagery.",
    "imagery": {
      "process_id": "NDVI",
      "imagery": {
        "process_id": "filter_daterange",
        "imagery": {
          "process_id": "get_collection",
          "name": "Sentinel2A-L1C"
        },
        "extent": [
          "2017-01-01T00:00:00Z",
          "2017-01-31T23:59:59Z"
        ]
      },
      "red": "4",
      "nir": "8"
    }
  }

EXAMPLE_FILE_LIST = ["TESTFILE1", "TESTFILE2", "TESTFILE3", "TESTFILE4"]

FILTER_ARGS = EXAMPLE_GRAPH

def handle_query(process_graph, result_files, filter_args, job_id):

    #TODO normalized --> filter_args sorted

    normalized = filter_args

    norm_hash = sha256(str(normalized)).hexdigest()

    result_hash = sha256(str(result_files)).hexdigest()

    #TODO check if Query is already there...


    original = process_graph

    #TODO data_pid --> get by filter_args name

    #TODO maybe add metadata...
    metadata = { "number_of_files": len(result_files)}

    #print(result)

#handle_query(EXAMPLE_GRAPH, EXAMPLE_FILE_LIST, FILTER_ARGS, "test")