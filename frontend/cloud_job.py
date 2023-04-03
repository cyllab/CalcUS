from django.conf import settings

from google.cloud import batch_v1


def create_container_job(calc_id: str) -> batch_v1.Job:
    client = batch_v1.BatchServiceClient()

    runnable = batch_v1.Runnable()
    runnable.container = batch_v1.Runnable.Container()
    runnable.container.image_uri = settings.COMPUTE_IMAGE
    runnable.container.commands = ["python", "manage.py", "run_calc", calc_id]

    task = batch_v1.TaskSpec()
    task.runnables = [runnable]

    resources = batch_v1.ComputeResource()
    resources.cpu_milli = 2000  # in milliseconds per cpu-second
    resources.memory_mib = 2048
    task.compute_resource = resources

    task.max_retry_count = 1
    task.max_run_duration = "3600s"

    group = batch_v1.TaskGroup()
    group.task_count = 1
    group.task_spec = task

    policy = batch_v1.AllocationPolicy.InstancePolicy()
    policy.machine_type = "e2-standard-4"
    instances = batch_v1.AllocationPolicy.InstancePolicyOrTemplate()
    instances.policy = policy
    acc = batch_v1.ServiceAccount()
    acc.email = settings.COMPUTE_SERVICE_ACCOUNT

    allocation_policy = batch_v1.AllocationPolicy()
    allocation_policy.instances = [instances]
    allocation_policy.service_account = acc

    job = batch_v1.Job()
    job.task_groups = [group]
    job.allocation_policy = allocation_policy
    job.labels = {"env": "testing", "type": "container"}

    # We use Cloud Logging as it's an out of the box available option
    job.logs_policy = batch_v1.LogsPolicy()
    job.logs_policy.destination = batch_v1.LogsPolicy.Destination.CLOUD_LOGGING

    create_request = batch_v1.CreateJobRequest()
    create_request.job = job
    create_request.job_id = "j" + calc_id.lower()

    create_request.parent = (
        f"projects/{settings.GCP_PROJECT_ID}/locations/{settings.GCP_LOCATION}"
    )

    return client.create_job(create_request)
