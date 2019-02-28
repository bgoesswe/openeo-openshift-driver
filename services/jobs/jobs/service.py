""" Job Management """

from os import environ
from nameko.rpc import rpc, RpcProxy
from nameko_sqlalchemy import DatabaseSession

from hashlib import sha256
from uuid import uuid4
import json
from .models import Base, Job, Query, QueryJob
from .schema import JobSchema, JobSchemaFull
# from .exceptions import BadRequest, Forbidden, APIConnectionError
# from .dependencies.task_parser import TaskParser
# from .dependencies.validator import Validator
from .dependencies.api_connector import APIConnector
from .dependencies.template_controller import TemplateController
import time
import random
import datetime

from git import Repo
from datetime import datetime
import pytz
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
        user_id = "openeouser"
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

            result = JobSchemaFull().dump(job).data

            if query:
                result["input_data"] = query.pid

            version_timestamp = datetime.strptime(result["metrics"]["start_time"], '%Y-%m-%d %H:%M:%S.%f')

            version_timestamp = version_timestamp.strftime('%Y%m%d%H%M%S.%f')

            result["metrics"]["back_end"] = "http://openeo.local.127.0.0.1.nip.io/version/"+version_timestamp

            return {
                "status": "success",
                "code": 200,
                "data": result
            }
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}/get"]).to_dict()

    @rpc
    def modify(self, user_id: str, job_id: str, process_graph: dict, title: str=None, description: str=None, 
               output: dict=None, plan: str=None, budget: int=None):
        user_id = "openeouser"
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}/patch"]).to_dict()
    
    @rpc
    def delete(self, user_id: str, job_id: str):
        user_id = "openeouser"
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}/delete"]).to_dict()

    @rpc
    def get_all(self, user_id: str):
        user_id = "openeouser"
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
        user_id = "openeouser"
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
            user_id = "openeouser"
            message = "Test0"
            try:
                job = self.db.query(Job).filter_by(id=job_id).first()
                message = "Test1"+str(job_id)
                valid, response = self.authorize(user_id, job_id, job)
                if not valid:
                    raise Exception(response)

                job.status = "running "+str(job.process_graph_id)
                self.db.commit()
                message = "Test2"
                # Get process nodes
                response = self.process_graphs_service.get_nodes(
                    user_id=user_id,
                    process_graph_id=job.process_graph_id)
                message = "Test3"
                if response["status"] == "error":
                    raise Exception(response)

                process_nodes = response["data"]
                message = str(job.process_graph_id)
                # Get file_paths
                filter_args = process_nodes[0]["args"]
                message = message + ";:"+str(filter_args)

                # quick fix
                if filter_args["extent"]:
                    spatial_extent = [filter_args["extent"]["extent"]["north"], filter_args["extent"]["extent"]["west"],
                                  filter_args["extent"]["extent"]["south"], filter_args["extent"]["extent"]["east"]]

                temporal = "{}/{}".format(filter_args["time"]["extent"][0], filter_args["time"]["extent"][1])
                message = str(spatial_extent) + "##" + temporal
                response = self.data_service.get_records(
                    detail="file_path",
                    user_id=user_id,
                    name=filter_args["name"],
                    spatial_extent=spatial_extent,
                    temporal_extent=temporal)
                #message = message #+ " ; " + str(response["data"])
                if response["status"] == "error":
                    raise Exception(response)
                #message = "Test6"
                start = datetime.datetime.now()
                query = self.handle_query(response["data"], filter_args)

                #filter_args["file_paths"] = response["data"]
                # job.status = "running "+str(query.normalized)
                # self.db.commit()

                # message = str(query)

                self.assign_query(query.pid, job_id)
                end = datetime.datetime.now()
                delta = end-start
                message = str(int(delta.total_seconds() * 1000))

                #message = str(self.get_provenance())
                # TODO: Calculate storage size and get storage class
                # TODO: Implement Ressource Management
                # storage_class = "storage-write"
                # storage_size = "5Gi"
                # processing_container = "docker-registry.default.svc:5000/execution-environment/openeo-processing"
                # min_cpu = "500m"
                # max_cpu = "1"
                # min_ram = "256Mi"
                # max_ram = "1Gi"
                # message = "Test7"
                # Create OpenShift objects
                # pvc = self.template_controller.create_pvc(self.api_connector, "pvc-" + job.id, storage_class, storage_size)
                # config_map = self.template_controller.create_config(self.api_connector, "cm-" + job.id, process_nodes)
                # message = "Test8"
                # Deploy container
                # logs, metrics =  self.template_controller.deploy(self.api_connector, job.id, processing_container,
                #    config_map, pvc, min_cpu, max_cpu, min_ram, max_ram)
                # message = "Test9"
                # pvc.delete(self.api_connector)

                # job.logs = logs
                # job.metrics = metrics

                # result_set = self.reexecute_query(user_id, query.pid)

                # message = str(result_set)


                #self.db.commit()

                #process_graph = self.process_graphs_service.get(user_id, job.process_graph_id)

                #if process_graph:
                #    process_graph = process_graph.process_graph
                start = datetime.datetime.now()
                job.metrics = self.create_context_model(job_id)
                end = datetime.datetime.now()
                delta = end-start
                message += "## CM: " + str(int(delta.total_seconds() * 1000))
                job.status = "finished " + str(message)
                self.db.commit()
                return
            except Exception as exp:
                job.status = "error: " + exp.__str__() + " " + str(message)
                self.db.commit()
            return

    @rpc
    def create_context_model(self, job_id):
        user_id = "openeouser"
        job = self.db.query(Job).filter_by(id=job_id).first()
        query = self.get_input_pid(job_id)

        context_model = {}
        # processing mockup
        process_graph = self.process_graphs_service.get(user_id, job.process_graph_id)
        output_hash = sha256(("OUTPUT"+str(process_graph)).encode('utf-8')).hexdigest()

        context_model['output_data'] = output_hash
        context_model['input_data'] = query.pid
        context_model['openeo_api'] = "0.3.1"
        #context_model['process_graph'] = process_graph
        context_model['job_id'] = job_id
        context_model['code_env'] = ["alembic==0.9.9",
                                     "amqp==1.4.9",
                                     "anyjson==0.3.3",
                                     "certifi==2018.8.24",
                                     "cffi==1.11.5",
                                     "chardet==3.0.4",
                                     "enum-compat==0.0.2",
                                     "eventlet==0.19.0",
                                     "gevent==1.3.6",
                                    "greenlet==0.4.14",
                                    "idna==2.7",
                                    "kombu==3.0.37",
                                    "Mako==1.0.7",
                                    "MarkupSafe==1.0",
                                    "marshmallow==2.15.3",
                                    "mock==2.0.0",
                                    "nameko==2.9.0",
                                    "nameko-sqlalchemy==1.4.0",
                                    "path.py==11.0.1",
                                    "pbr==4.0.4",
                                    "psycopg2==2.7.4",
                                    "pycparser==2.18",
                                    "pyOpenSSL==18.0.0",
                                    "python-dateutil==2.7.3",
                                    "python-editor==1.0.3",
                                    "PyYAML==3.12",
                                    "requests==2.20.0",
                                    "six==1.11.0",
                                    "SQLAlchemy==1.2.8",
                                    "urllib3==1.23",
                                    "Werkzeug==0.14.1",
                                    "wincertstore==0.2",
                                    "wrapt==1.10.11"]
        context_model['interpreter'] = "Python 3.7.1"
        context_model['start_time'] = str(job.created_at)
        context_model['end_time'] = str(job.created_at+datetime.timedelta(random.randint(1, 3), random.randint(0, 59)))#datetime.datetime.fromtimestamp(time.time())

        # cm = get_job_cm(job_id)

        return context_model

    @rpc
    def version_current(self):

        version_info = self.get_git()
        return {
            "status": "success",
            "code": 200,
            "data": version_info
        }

    def get_commit_by_timestamp(self, timestamp):

        try:
            repo = Repo("openeo-openshift-driver/")

            timestamp = datetime.strptime(timestamp, '%Y%m%d%H%M%S.%f')  # datetime(2018, 5, 5, 23, 30,tzinfo=utc)
            timestamp = pytz.utc.localize(timestamp)

            date_buffer = None
            git_info = {}
            for commit in repo.iter_commits("master"):
                commit_date = commit.committed_datetime
                if commit_date <= timestamp:
                    if date_buffer:
                        if commit_date > date_buffer:
                            date_buffer = commit_date
                            git_info["branch"] = commit.name_rev.split(" ")[1]
                            git_info["commit"] = commit.name_rev.split(" ")[0]

                    else:
                        date_buffer = commit_date
                        git_info["branch"] = commit.name_rev.split(" ")[1]
                        git_info["commit"] = commit.name_rev.split(" ")[0]

        except(Exception):
            return None

        return git_info


    @rpc
    def version(self, timestamp: str):

        git_info = self.get_commit_by_timestamp(timestamp)

        if not git_info:
            return {
                "status": "error",
                "code": 500,
                "data": "timestamp is not formatted correctly, format e.g. 20180528101608.659892"
            }

        version_info = self.get_git()
        version_info["branch"] = git_info["branch"]
        version_info["commit"] = git_info["commit"]
        version_info["diff"] = "None"
        version_info["timestamp"] = str(datetime.strptime(timestamp, '%Y%m%d%H%M%S.%f'))

        return {
            "status": "success ",
            "code": 200,
            "data": version_info
        }

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
        user_id = "openeouser"
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}~1results/delete"]).to_dict()
    
    @rpc
    def get_results(self, user_id: str, job_id: str):
        user_id = "openeouser"
        try:
            raise Exception("Not implemented yet!")
        except Exception as exp:
            return ServiceException(500, user_id, str(exp),
                links=["#tag/Job-Management/paths/~1jobs~1{job_id}~1results/get"]).to_dict()


    def authorize(self, user_id, job_id, job):
        user_id = "openeouser"
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
        normalized = normalized.strip()
        print(normalized)
        norm_hash = sha256(normalized.encode('utf-8')).hexdigest()
        print(norm_hash)

        result_list = str(result_files).split("]")[0]
        result_list += "]"
        result_list = result_list.replace(" ", "")
        result_list = result_list.replace("\t", "")
        result_list = result_list.replace("\n", "")
        # TESTCASE1
        #result_list = result_list.replace("S2A_MSIL1C_20170104T101402_N0204_R022_T32TPR_20170104T101405",
        #                                  "S2A_MSIL1C_20170104T101402_N0204_R022_T32TPR_20170104T101405_NEW")
        result_list = result_list.encode('utf-8')
        result_list = result_list.strip()


        result_hash = sha256(result_list).hexdigest()

        existing = self.db.query(Query).filter_by(norm_hash=norm_hash, result_hash=result_hash).first()

        if existing:
            return existing

        dataset_pid = str(filter_args["name"])
        orig_query = str(filter_args)
        metadata = str({"number_of_files": len(result_files.split("\n"))})

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

    @rpc
    def get_query_by_pid(self, query_pid):
        return self.db.query(Query).filter_by(pid=query_pid).first()

    @rpc
    def get_dataset_by_pid(self, query_pid):
        query = self.db.query(Query).filter_by(pid=query_pid).first()

        dataset = None
        if query:
            dataset = query.dataset_pid

        return dataset

    @rpc
    def get_querydata_by_pid(self, query_pid):
        query = self.db.query(Query).filter_by(pid=query_pid).first()

        if query:
            query = str(query.normalized)

        return query

    @rpc
    def reexecute_query(self, user_id, query_pid):
        user_id = "openeouser"
        query = self.db.query(Query).filter_by(pid=query_pid).first()

        filter_args = query.original

        json_acceptable_string = filter_args.replace("'", "\"")
        json_acceptable_string = json_acceptable_string.replace("None", "null")
        filter_args = json.loads(json_acceptable_string)

        # quick fix
        spatial_extent = [filter_args["extent"]["extent"]["north"], filter_args["extent"]["extent"]["west"],
                          filter_args["extent"]["extent"]["south"], filter_args["extent"]["extent"]["east"]]

        temporal = "{}/{}".format(filter_args["time"]["extent"][0], filter_args["time"]["extent"][1])

        response = self.data_service.get_records(
            detail="file_path",
            user_id=user_id,
            name=filter_args["name"],
            spatial_extent=spatial_extent,
            temporal_extent=temporal)

        if response["status"] == "error":
            raise Exception(response)

        filter_args["file_paths"] = response["data"]
        # TESTCASE1
        #filter_args["file_paths"] = filter_args["file_paths"].replace("S2A_MSIL1C_20170104T101402_N0204_R022_T32TPR_20170104T101405",
        #                                  "S2A_MSIL1C_20170104T101402_N0204_R022_T32TPR_20170104T101405_NEW")
        return filter_args["file_paths"]

    def run_cmd(self, command):
        import subprocess
        result = subprocess.run(command.split(), stdout=subprocess.PIPE)
        return result.stdout.decode("utf-8")

    def get_git(self):
        import hashlib
        git_cmd = "git --git-dir=openeo-openshift-driver/.git "
        # print(git_cmd)
        #URL = "https://github.com/bgoesswe/openeo-openshift-driver.git"
        #CMD_GIT_CLONE = "{0} clone {1}".format(git_cmd, URL)
        #CMD_CD_GIT = "cd openeo-openshift-driver"
        #CMD_LS_GIT = "ls"
        CMD_GIT_URL = "{0} config --get remote.origin.url".format(git_cmd)
        CMD_GIT_BRANCH = "{0} branch".format(git_cmd)
        CMD_GIT_COMMIT = "{0} log".format(git_cmd)  # first line
        CMD_GIT_DIFF = "{0} diff".format(git_cmd)  # Should do that ?

        print("Get Git Info")

        #clone = self.run_cmd(CMD_GIT_CLONE)



        #cd = self.run_cmd(CMD_CD_GIT)

        git_url = self.run_cmd(CMD_GIT_URL).split("\n")[0]
        git_commit = self.run_cmd(CMD_GIT_COMMIT).split("\n")[0].replace("commit", "").strip()
        git_diff = self.run_cmd(CMD_GIT_DIFF)
        # remove not needed encodings
        git_diff = git_diff.replace("\n", "")
        git_diff = git_diff.replace("\n", "")
        git_diff = git_diff.strip()

        git_diff = hashlib.sha256(git_diff.encode("utf-8"))
        git_diff = git_diff.hexdigest()

        git_branch = self.run_cmd(CMD_GIT_BRANCH).replace("*", "").strip()

        cm_git = {'url': git_url,
                  'branch': git_branch,
                  'commit': git_commit,
                  'diff': git_diff,
                  }

        return cm_git

    def get_provenance(self):
        context_model = {}

        installed_packages = self.run_cmd("pip freeze")


        #installed_packages = pip.get_installed_distributions()
        #installed_packages_list = sorted(["%s==%s" % (i.key, i.version)
         #                                 for i in installed_packages])
        context_model["code_env"] = installed_packages

        context_model["backend_env"] = self.get_git("git")

        return context_model


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
