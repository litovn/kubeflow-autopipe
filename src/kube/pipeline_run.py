import kfp
from .pipeline_auth import KFPClientManager


def pipeline_run(pvc_name, pipeline_func, pipeline_filename):
    """
    Generate a run to execute the defined pipeline

    :param pvc_name: name of the pvc to store data into
    :param pipeline_func: pipeline function to execute
    :param pipeline_filename: name of pipeline yaml config file
    """
    # Create a request to connect to the Kubeflow framework by DeployKF, using your credentials
    kfp_client_manager = KFPClientManager(
        api_url="https://deploykf.example.com:8443/pipeline",
        skip_tls_verify=True,
        dex_username="user1@example.com",
        dex_password="user1",
        dex_auth_type="local"
    )
    client = kfp_client_manager.create_kfp_client()

    # Set namespace in the Kubernetes cluster
    client.set_user_namespace('team-1')

    # Compile the pipeline into a package
    kfp.compiler.Compiler().compile(pipeline_func=pipeline_func, package_path=pipeline_filename)

    # Run the experiment
    run_name = f"Pipeline run for {pvc_name}"
    run = client.create_run_from_pipeline_package(
        pipeline_file=pipeline_filename,
        arguments={
            'pvc_name': pvc_name
        },
        run_name=run_name,
        experiment_name='auto_kubepipe',
        namespace='team-1',
        enable_caching=False
    )
    run_id = str(run.run_id)
    client.wait_for_run_completion(run_id=run_id, timeout=3600, sleep_duration=10)

