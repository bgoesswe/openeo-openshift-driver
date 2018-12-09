""" Job Management """

from os import environ
from nameko.rpc import rpc, RpcProxy
from nameko_sqlalchemy import DatabaseSession

from hashlib import sha256
from uuid import uuid4

from .models import Base, Job, Query, QueryJob
from .schema import JobSchema, JobSchemaFull
# from .exceptions import BadRequest, Forbidden, APIConnectionError
# from .dependencies.task_parser import TaskParser
# from .dependencies.validator import Validator
from .dependencies.api_connector import APIConnector
from .dependencies.template_controller import TemplateController


service_name = "jobs"


class ServiceException(Exception):
    """ServiceException raises if an exception occured while processing the 
    request. The ServiceException is mapping any exception to a serializable
    format for the API gateway.
    """

    def __init__(self, code: int, user_id: str, msg: str,
                 internal: bool=True, links: list=[]):
        self._service = service_name
        self._code = code
        self._user_id = user_id
        self._msg = msg
        self._internal = internal
        self._links = links

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

class JobService:
    """Management of batch processing tasks (jobs) and their results.
    """

    name = service_name
    db = DatabaseSession(Base)
    process_graphs_service = RpcProxy("process_graphs")
    data_service = RpcProxy("data")
    api_connector = APIConnector()
    template_controller = TemplateController()

    @rpc
    def get(self, user_id: str, job_id: str):
        try:
            job = self.db.query(Job).filter_by(id=job_id).first()

            valid, response = self.authorize(user_id, job_id, job)
            if not valid: 
                return response

            response = self.process_graphs_service.get(user_id, job.process_graph_id)
            if response["status"] == "error":
               return response
            
            job.process_graph = response["data"]["process_graph"]

            query = self.get_input_pid(job_id)

            return {
                "status": "success",
                "code": 200,
                "input_data": query.pid,
                "data": JobSchemaFull().dump(job).data
            }
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}/get"]).to_dict()

    @rpc
    def modify(self, user_id: str, job_id: str, process_graph: dict, title: str=None, description: str=None, 
               output: dict=None, plan: str=None, budget: int=None):
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}/patch"]).to_dict()
    
    @rpc
    def delete(self, user_id: str, job_id: str):
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}/delete"]).to_dict()

    @rpc
    def get_all(self, user_id: str):
        try:
            jobs = self.db.query(Job).filter_by(user_id=user_id).order_by(Job.created_at).all()

            return {
                "status": "success",
                "code": 200,
                "data": JobSchema(many=True).dump(jobs).data
            }
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs/get"]).to_dict()
    @rpc
    def create(self, user_id: str, process_graph: dict, title: str=None, description: str=None, output: dict=None, 
                   plan: str=None, budget: int=None):
        try:
            process_response = self.process_graphs_service.create(
                user_id=user_id, 
                **{"process_graph": process_graph})
            
            if process_response["status"] == "error":
               return process_response
            
            process_graph_id = process_response["service_data"]

            job = Job(user_id, process_graph_id, title, description, output, plan, budget)

            job_id = str(job.id)
            self.db.add(job)
            self.db.commit()

            return {
                "status": "success",
                "code": 201,
                "headers": {"Location": "jobs/" + job_id }
            }
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs/post"]).to_dict()
    
    @rpc
    def process(self, user_id: str, job_id: str):
        message = "Test0"
        try:
            job = self.db.query(Job).filter_by(id=job_id).first()
            message = "Test1"
            valid, response = self.authorize(user_id, job_id, job)
            if not valid:
                raise Exception(response)

            job.status = "running"
            self.db.commit()
            message = "Test2"
            # Get process nodes
            response = self.process_graphs_service.get_nodes(
                user_id=user_id,
                process_graph_id= job.process_graph_id)
            message = "Test3"
            if response["status"] == "error":
               raise Exception(response)
            
            process_nodes = response["data"]
            message = "Test4"
            # Get file_paths
            filter_args = process_nodes[0]["args"]
            message = filter_args

            # quick fix
            spatial_extent = [filter_args["extent"]["extent"]["north"], filter_args["extent"]["extent"]["west"],
                              filter_args["extent"]["extent"]["south"], filter_args["extent"]["extent"]["east"]]

            temporal = "{}/{}".format(filter_args["time"]["extent"][0], filter_args["time"]["extent"][1])
            message = str(spatial_extent) + "##"+temporal
            response = self.data_service.get_records(
                detail="file_path",
                user_id=user_id, 
                name=filter_args["name"],
                spatial_extent=spatial_extent,
                temporal_extent=temporal)
            message = "Test5"
            if response["status"] == "error":
               raise Exception(response)
            message = "Test6"
            filter_args["file_paths"] = response["data"]

            query = self.handle_query(filter_args["file_paths"], filter_args)

            #job.status = "running "+str(query.normalized)
            #self.db.commit()

            message = str(query)

            self.assign_query(query.pid, job_id)

            message = "Really finishd !!"
            # TODO: Calculate storage size and get storage class
            # TODO: Implement Ressource Management
            #storage_class = "storage-write"
            #storage_size = "5Gi"
            #processing_container = "docker-registry.default.svc:5000/execution-environment/openeo-processing"
            #min_cpu = "500m"
            #max_cpu = "1"
            #min_ram = "256Mi"
            #max_ram = "1Gi"
            #message = "Test7"
            # Create OpenShift objects
            #pvc = self.template_controller.create_pvc(self.api_connector, "pvc-" + job.id, storage_class, storage_size)
            #config_map = self.template_controller.create_config(self.api_connector, "cm-" + job.id, process_nodes)
            #message = "Test8"
            # Deploy container
            #logs, metrics =  self.template_controller.deploy(self.api_connector, job.id, processing_container,
            #    config_map, pvc, min_cpu, max_cpu, min_ram, max_ram)
            #message = "Test9"
            #pvc.delete(self.api_connector)
            
            #job.logs = logs
            #job.metrics = metrics

            query = self.get_input_pid(job_id)
            message = str(query)
            job.status = "finished "+message
            self.db.commit()
            return
        except Exception as exp:
            job.status = "error: " + exp.__str__()+ " "+str(message)
            self.db.commit()
            return

    # TODO: If build should be automated using an endpoint e.g. /build the following can be 
    # activated and adapted
    # @rpc
    # def build(self, user_id: str):
    #     try:
    #         status, log, obj_image_stream = self.template_controller.build(
    #             self.api_connector,
    #             environ["CONTAINER_NAME"],
    #             environ["CONTAINER_TAG"],
    #             environ["CONTAINER_GIT_URI"], 
    #             environ["CONTAINER_GIT_REF"], 
    #             environ["CONTAINER_GIT_DIR"])
    #     except Exception as exp:
    #         return ServiceException(500, user_id, str(exp),
    #             links=["#tag/Job-Management/paths/~1jobs~1{job_id}~1results/delete"]).to_dict()
    
    @rpc
    def cancel_processing(self, user_id: str, job_id: str):
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}~1results/delete"]).to_dict()
    
    @rpc
    def get_results(self, user_id: str, job_id: str):
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}~1results/get"]).to_dict()


    def authorize(self, user_id, job_id, job):
        if job is None:
            return False, ServiceException(400, user_id, "The job with id '{0}' does not exist.".format(job_id), 
                internal=False, links=["#tag/Job-Management/paths/~1data/get"]).to_dict()

        # TODO: Permission (e.g admin)
        if job.user_id != user_id:
            return False, ServiceException(401, user_id, "You are not allowed to access this ressource.", 
                internal=False, links=["#tag/Job-Management/paths/~1data/get"]).to_dict()
        
        return True, None

    # QUERY STORE functionallity

    def order_dict(self, dictionary):
        return {k: self.order_dict(v) if isinstance(v, dict) else v
                for k, v in sorted(dictionary.items())}

    def handle_query(self, result_files, filter_args):

        # normalized query, sorted query...
        normalized = self.order_dict(filter_args)
        normalized = str(normalized)
        print(normalized)
        norm_hash = sha256(normalized.encode('utf-8')).hexdigest()
        print(norm_hash)
        result_list = str(result_files)
        result_list = result_list.encode('utf-8')

        result_hash = sha256(result_list).hexdigest()

        existing = self.db.query(Query).filter_by(norm_hash=norm_hash, result_hash=result_hash).first()

        if existing:
            return existing

        dataset_pid = str(filter_args["name"])
        orig_query = str(filter_args)
        metadata = str({"number_of_files": len(result_files)})

        new_query = Query(dataset_pid, orig_query, normalized, norm_hash,
                 result_hash, metadata)

        self.db.add(new_query)
        self.db.commit()

        return new_query

    def assign_query(self, query_pid, job_id):
        queryjob = QueryJob(query_pid, job_id)
        self.db.add(queryjob)
        self.db.commit()

    def get_input_pid(self, job_id):
        queryjob = self.db.query(QueryJob).filter_by(job_id=job_id).first()

        return self.db.query(Query).filter_by(pid=queryjob.query_pid).first()

    # @rpc
    # def get_job(self, user_id, job_id):
    #     try:
    #         job = self.db.query(Job).filter_by(id=job_id).first()

    #         if not job:
    #             raise BadRequest("Job with id '{0}' does not exist.").format(job_id)

    #         if job.user_id != user_id:
    #             raise Forbidden("You don't have the permission to access job with id '{0}'.").format(job_id)

    #         return {
    #             "status": "success",
    #             "data": JobSchemaFull().dump(job).data
    #         }
    #     except BadRequest:
    #         return {"status": "error", "service": self.name, "key": "BadRequest", "msg": str(exp)}
    #     except Forbidden:
    #         return {"status": "error", "service": self.name, "key": "Forbidden", "msg": str(exp)}
    #     except Exception as exp:
    #         return {"status": "error", "service": self.name, "key": "InternalServerError", "msg": str(exp)}
    
    # @rpc
    # def process_job(self, job_id):
    #     try:
    #         job = self.db.query(Job).filter_by(id=job_id).first()
    #         tasks = self.db.query(Task).filter_by(job_id=job_id).all()
    #         processes = self.process_service.get_all_processes_full()["data"]

    #         tasks = sorted(tasks, key=lambda task: task.seq_num)

    #         job.status = "running"
    #         self.db.commit()

    #         data_filter = tasks[0]

    #         pvc = self.data_service.prepare_pvc(data_filter)["data"]

    #         # TODO: Implement in Extraction Service
    #         filter = tasks[0]
    #         product = filter.args["product"]
    #         start = filter.args["filter_daterange"]["from"]
    #         end = filter.args["filter_daterange"]["to"]
    #         left = filter.args["filter_bbox"]["left"]
    #         right = filter.args["filter_bbox"]["right"]
    #         top = filter.args["filter_bbox"]["top"]
    #         bottom = filter.args["filter_bbox"]["bottom"]
    #         srs = filter.args["filter_bbox"]["srs"]

    #         bbox = [top, left, bottom, right]

    #         # in_proj = Proj(init=srs)
    #         # out_proj = Proj(init='epsg:4326')
    #         # in_x1, in_y1 = bottom, left
    #         # in_x2, in_y2 = top, right
    #         # out_x1, out_y1 = transform(in_proj, out_proj, in_x1, in_y1)
    #         # out_x2, out_y2 = transform(in_proj, out_proj, in_x2, in_y2)
    #         # bbox = [out_x1, out_y1, out_x2, out_y2]

    #         file_paths = self.data_service.get_records(qtype="file_paths", qname=product, qgeom=bbox, qstartdate=start, qenddate=end)["data"]
    #         tasks[0].args["file_paths"] = file_paths

    #         pvc = self.template_controller.create_pvc(self.api_connector, "pvc-" + str(job.id), "storage-write", "5Gi")     # TODO: Calculate storage size and get storage class
    #         previous_folder = None
    #         for idx, task in enumerate(tasks):
    #             try:
    #                 template_id = "{0}-{1}".format(job.id, task.id)

    #                 for p in processes:
    #                     if p["process_id"] == task.process_id:
    #                         process = p
                    
    #                 config_map = self.template_controller.create_config(
    #                     self.api_connector, 
    #                     template_id, 
    #                     {
    #                         "template_id": template_id,
    #                         "last": previous_folder,
    #                         "args": task.args
    #                     })
                    
    #                 image_name = process["process_id"].replace("_", "-").lower() # TODO: image name in process spec

    #                 status, log, obj_image_stream = self.template_controller.build(
    #                     self.api_connector, 
    #                     template_id, 
    #                     image_name,
    #                     "latest",   # TODO: Implement tagging in process service
    #                     process["git_uri"], 
    #                     process["git_ref"], 
    #                     process["git_dir"])

    #                 status, log, metrics =  self.template_controller.deploy(
    #                     self.api_connector, 
    #                     template_id,
    #                     obj_image_stream, 
    #                     config_map,
    #                     pvc,
    #                     "500m",     # TODO: Implement Ressource Management
    #                     "1", 
    #                     "256Mi", 
    #                     "1Gi")
                    
    #                 previous_folder = template_id
    #             except APIConnectionError as exp:
    #                 task.status = exp.__str__()
    #                 self.db.commit()
    #         pvc.delete(self.api_connector)
    #         job.status = "finished"
    #         self.db.commit()
    #     except Exception as exp:
    #         job.status = str(exp)
    #         self.db.commit()
