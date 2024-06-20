import kfp
from pipeline_auth import KFPClientManager


def pipeline_run(video_input_path, pvc_name, pipeline_func, pipeline_filename):
    """
    Generate a run to execute the defined pipeline

    :param video_input_path: path to video file to process
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

    # Compile the pipeline
    kfp.compiler.Compiler().compile(pipeline_func=pipeline_func, package_path=pipeline_filename)

    # Run the experiment
    run_name = f"Pipeline run for {pvc_name}"
    client.create_run_from_pipeline_package(
        pipeline_file=pipeline_filename,
        arguments={
            'video_url': video_input_path,
            'pvc_name': pvc_name
        },
        run_name=run_name,
        namespace='team-1'
    )
