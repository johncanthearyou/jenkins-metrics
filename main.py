from dotenv import dotenv_values
from fastapi import FastAPI
import json as json_util
import numpy
import requests
from requests.auth import HTTPBasicAuth
import pymongo

mongo = pymongo.MongoClient("mongodb://localhost:27017")
metrics_db = mongo["jenkins-metrics"]
jenkins_url = "http://localhost:8080"
env = dotenv_values()
app = FastAPI()

@app.get("/")
def get_jobs():
    return metrics_db["jobs"].distinct("job")

@app.get("/job/{job}")
def get_job_metrics(job):
    job_durations = [job_entry["durationMillis"]/60000 for job_entry in metrics_db["jobs"].find({"job": job})]
    return {
        "mean": numpy.mean(job_durations),
        "st dev": numpy.std(job_durations),
        "median": numpy.median(job_durations),
        "n": len(job_durations)
    }

@app.get("/job/{job}/build/{build}")
def get_build_metrics(job, build):
    return metrics_db["jobs"].find_one({"id": f"{job}#{build}"})

@app.post("/job/{job}/build/{build}")
def update_build_metrics(job, build):
    response = requests.get(
        url=f"{jenkins_url}/job/{job}/{build}/wfapi",
        auth=HTTPBasicAuth(env["USER"], env["PASS"])
    )
    json = json_util.loads(response.content)
    json["job"] = job
    json["build"] = json["id"]
    json["id"] = f"{job}#{json['id']}"
    return json

@app.post("/")
def update_jobs():
    # get list of builds for which to update metrics
    response = requests.get(
        url=f"{jenkins_url}/api/json?tree=jobs[name,builds[number]]",
        auth=HTTPBasicAuth(env["USER"], env["PASS"])
    )
    json = json_util.loads(response.content)
    for job in json["jobs"]:
        for build in job["builds"]:
            build_metrics = update_build_metrics(job["name"], build["number"])
            find_result = metrics_db["jobs"].find_one({"id": build_metrics["id"]})
            if find_result == None:
                metrics_db["jobs"].insert_one(build_metrics)

    return "success"
