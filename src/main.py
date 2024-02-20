from dotenv import dotenv_values
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json as json_util
import numpy
import pymongo
import mssql
import requests
from requests.auth import HTTPBasicAuth

db_connection = mssql.connect()
env = dotenv_values(".env")
metrics_db = pymongo.MongoClient(env['MONGO_CONNECTION'])["jenkins-metrics"]
metrics_jobs = metrics_db["jobs"]

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def get_jobs():
    return metrics_jobs.distinct("job")

@app.post("/")
def update_all_metrics():
    jobs = get_jobs()
    ingested_builds = []
    for job in jobs:
        for build in job["builds"]:
            ingested_builds += [update_build_metrics(job["name"], build["number"])["id"]]

    return ingested_builds

@app.get("/job/{job:path}")
def get_job_metrics(job:str):
    build_entries = [job_entry for job_entry in metrics_jobs.find({"job": job}, projection={'_id': False, '_links': False, 'stages': False})]
    build_durations = [job_entry["durationMillis"]/60000 for job_entry in build_entries]
    return {
        "name": job,
        "mean": '%.3f'%(numpy.mean(build_durations)),
        "st_dev": '%.3f'%(numpy.std(build_durations)),
        "median": '%.3f'%(numpy.median(build_durations)),
        "build_samples": len(build_entries),
        "builds": list(reversed(build_entries))
    }

@app.post("/build/{build}/job/{job:path}")
def update_build_metrics(job, build):
    response = requests.get(
        url=f"{env['JENKINS_URL']}/job/{job.replace("/", "/job/")}/{build}/wfapi",
        auth=HTTPBasicAuth(env["JENKINS_USER"], env["JENKINS_TOKEN"])
    )
    build_metrics = json_util.loads(response.content)
    build_metrics["job"] = job
    build_metrics["build"] = build_metrics["id"]
    build_metrics["id"] = f"{job}#{build_metrics['id']}"

    # Update database
    find_result = metrics_jobs.find_one_and_replace(
        {"id": build_metrics["id"]},
        build_metrics
    )
    if find_result == None:
        metrics_jobs.insert_one(build_metrics)

    return build_metrics


@app.get("/build/{build}/job/{job:path}")
def get_build_metrics(job, build):
    build_data = metrics_jobs.find_one({"id": f"{job}#{build}"}, projection={'_id': False})
    return build_data


def get_jobs(root_folder=""):
    url = env['JENKINS_URL']
    if root_folder != "":
        url += "/job/"
    url += f"{root_folder.replace("/", "/job/")}/api/json?tree=jobs[name,builds[number]]"
    response = requests.get(
        url=url,
        auth=HTTPBasicAuth(env["JENKINS_USER"], env["JENKINS_TOKEN"])
    )
    all_jobs = json_util.loads(response.content)["jobs"]
    
    pipeline_jobs = []
    just_jobs = filter(
        lambda job: job["_class"] == "org.jenkinsci.plugins.workflow.job.WorkflowJob",
        all_jobs
    )
    for job in just_jobs:
        if root_folder == "":
            job["name"] = job['name']
        else:
            job["name"] = f"{root_folder}/{job['name']}"
        pipeline_jobs += [job]
    
    just_folders = filter(
        lambda job: job["_class"] == "com.cloudbees.hudson.plugins.folder.Folder",
        all_jobs
    )
    for folder in just_folders:
        new_folder_path = f"{root_folder}/{folder['name']}"
        if root_folder == "":
            new_folder_path = folder['name']
        pipeline_jobs += get_jobs(new_folder_path)

    return pipeline_jobs