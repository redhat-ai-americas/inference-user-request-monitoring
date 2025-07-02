# inference-user-request-monitoring

This project contains a bunch of setup in your OpenShift cluster to use existing functionality to build a Grafana dashboard to track which users are making active use of LLMs deployed on your cluster.

## Production Use

This repository is strictly for demo purposes. For production, we would recommend the MaaS setup, but in cases where no API Gateway is present, this can be a decent quick stand-in to achieve auditability. Furthermore, if you decide to use this, you will need to adjust the RBAC in Grafana, as this gives every logged in user admin permissions by default.

## What it sets up

* ODF with Noobaa
* OpenShift Logging
* Loki
* Grafana

## How to use this repo

Loki requires a lot of resources for some reason. You will need to add several (3 in my experience) additional worker nodes to make it work.

You will also need OpenShift AI enabled. The dashboard specifically looks for vLLM running in KServe, so that is taken as a given.

Run `setup.sh` to stand up all the necessary infrastructure. Then log into Grafana with your OpenShift user and upload the [grafana json file](dashboard/vllm-logging-dashboard.json) as dashboards.

## References

* odf-helm is borrowed with a special thank you from https://github.com/jharmison-redhat/openshift-setup in openshift-setup/charts/odf-operator
* storage is borrowed from https://github.com/rh-aiservices-bu/genai-rhoai-poc-template/blob/dev/common-utils/mcgw/config/
* Grafana deployment: https://community.grafana.com/t/problems-retrieving-loki-logs-in-grafana-on-openshift/89257/18
* Loki setup: https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/logging/logging-6-2#log6x-loki-6-2
