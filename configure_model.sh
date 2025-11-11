while getopts ":n:" opt;
do
    case $opt in
        n)
            NAMESPACE=$OPTARG
            ;;
        \?)
          echo "Invalid option: -$OPTARG" >&2
          exit 1
          ;;
        :)
          echo "Option -$OPTARG requires an argument." >&2
          exit 1
          ;; 
    esac
done
shift $((OPTIND-1))
MODEL=$1

if [[ -z $MODEL ]]
then
    echo "You must pass a model argument."
    exit 1
fi
if [[ -z $NAMESPACE ]]
then
    NAMESPACE_ARG=''
else
    NAMESPACE_ARG="-n $NAMESPACE"
fi

if ! $( oc get configmap vllm-monitoring-middleware $NAMESPACE_ARG >/dev/null 2>&1 )
then
    oc create configmap vllm-monitoring-middleware $NAMESPACE_ARG --from-file=dashboard/middleware.py --from-literal=__init__.py='#some stuff'
fi

oc get ServingRuntime $NAMESPACE_ARG $MODEL -o json | jq '.spec.containers[0].volumeMounts += [{"name": "vllm-monitoring-middleware", "mountPath": "/opt/app-root/middleware"}] | .spec.volumes += [{"name": "vllm-monitoring-middleware", "configMap": {"name": "vllm-monitoring-middleware"}}]' | oc apply -f -
oc get InferenceService $NAMESPACE_ARG $MODEL -o json | jq '.spec.predictor.model.args += ["--middleware", "middleware.middleware.OpenAITokenLoggerMiddleware"]' | oc apply -f -
