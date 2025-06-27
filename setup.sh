oc apply -f namespaces.yaml

# RHOAI must be installed before this step.
oc patch -n redhat-ods-applications-auth-provider Authorino authorino -p '{"spec":{"logLevel": "debug"}}' --type=merge

cd odf-helm
manifests="$(helm template -n openshift-storage odf-operator . -f example-mcgw-only-values.yaml)"; while ! echo "$manifests" | oc apply -n openshift-storage -f-; do sleep 5; done
cd ../

oc apply -f storage/
while ! oc apply -f openshift-logging; do sleep 5; done

cd loki-helm
AWSACCESSKEYID=$(oc get secret -n openshift-storage demo -o json | jq -r .data.AWS_ACCESS_KEY_ID | tr -d '\n' | tr -d '\r\n' | base64 -d)
AWSSECRETACCESSKEY=$(oc get secret -n openshift-storage demo -o json | jq -r .data.AWS_SECRET_ACCESS_KEY | tr -d '\n' | tr -d '\r\n' | base64 -d)
BUCKETNAME=$(oc get configmap -n openshift-storage demo -o json | jq -r .data.BUCKET_NAME | tr -d '\n' | tr -d '\r\n')
manifests="$(helm template loki . --set defaultBucket="$BUCKETNAME" --set accessKeyId="$AWSACCESSKEYID" --set secretAccessKey="$AWSSECRETACCESSKEY")"; while ! echo "$manifests" | oc apply -f-; do sleep 5; done
cd ../

cd grafana-helm
CLUSTER_INFO=$(oc cluster-info | grep -Po "api.*:6443")
CLUSTER_ROUTE=${CLUSTER_INFO:4:-5}
manifests="$(helm template grafana . --set clusterRoute="$CLUSTER_ROUTE")"; while ! echo "$manifests" | oc apply -f-; do sleep 5; done
