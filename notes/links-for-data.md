This pattern shows each of the available builds's URL for every job:
  * <JENKINS_URL>/api/json?pretty=true&tree=jobs[name,url,builds[number,url]]
  * This will be used essentially as a gateway to get to the granular data (below) for all the jobs

This pattern shows detailed data for a specific job's build:
  * <JENKINS_URL>/job/<JOB_NAME>/<BUILD_NUMBER>/wfapi
