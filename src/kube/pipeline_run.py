import kfp
from .pipeline_auth import KFPClientManager

# Namespace defined and used with deployKF
NAMESPACE = 'team-1'


def pipeline_run(pvc_name, pipeline_func, pipeline_filename):
    """
    Initiates a Kubeflow pipeline run using a specified pipeline function and configuration.

    :param pvc_name: The name of the PVC to store component outputs into
    :param pipeline_func: Kubeflow Pipeline function to execute
    :param pipeline_filename: Name of Kubeflow Pipeline YAML configuration file
    """
    # Create a Kubeflow Pipelines client using the KFPClientManager, which handles authentication and connection
    # details to the Kubeflow Pipelines API.
    kfp_client_manager = KFPClientManager(
        api_url="https://deploykf.example.com:8443/pipeline",
        skip_tls_verify=True,
        dex_username="user1@example.com",
        dex_password="user1",
        dex_auth_type="local"
    )
    client = kfp_client_manager.create_kfp_client()

    # Set Kubernetes namespace for the pipeline run
    client.set_user_namespace(NAMESPACE)

    # Compile the provided pipeline function into a YAML configuration file, saving it with the specified filename
    kfp.compiler.Compiler().compile(pipeline_func=pipeline_func, package_path=pipeline_filename)

    # Submit the pipeline run to the Kubeflow Pipelines environment
    run_name = f"Pipeline run for {pvc_name}"
    run = client.create_run_from_pipeline_package(
        pipeline_file=pipeline_filename,
        arguments={
            'pvc_name': pvc_name
        },
        run_name=run_name,
        experiment_name='auto_kubepipe',
        namespace=NAMESPACE,
        enable_caching=False
    )

    # Waits for the pipeline run to complete
    run_id = str(run.run_id)
    client.wait_for_run_completion(run_id=run_id, timeout=3600, sleep_duration=10)

