import os
import time
import yaml
import subprocess
import logging
import argparse
from dotenv import load_dotenv

from kfp import dsl
from kfp.kubernetes import mount_pvc

from kube.pvc_manager import *
from kube.pipeline_run import *


# Configure logging to display information based on your needs
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def load_dag_configuration(dag_path):
    """
    Load the yaml dag configuration file, to extract the required information

    :param dag_path: The file path to the YAML configuration file
    :return: A tuple containing lists of components, dependencies, and the initial input media file path
    """
    with open(dag_path, 'r') as file:
        data = yaml.safe_load(file)
        return data['System']['components'], data['System']['dependencies'], data['System']['input_media']


# With download_from_pvc method defined in pvc_manager.py, it might be possible to search for the output file path
# saved by the previous component (independently of its name) in the PVC and download it to the local machine, then
# use it as the input for the next component.
# -----
# This method is not used, because it would imply to create an updated pod after each component by overwriting the
# previous one, which is not an optimal approach.
# -----
# instead we consider that the component will save their output file as: output_name + ".tar.gz"
# where output_name = os.path.basename(output_path_dir)
"""
def get_output_filepath(output_dir: str):
    files = os.listdir(output_dir)
    if not files:
        logging.error(f"No files found in directory: {output_dir}")
    file_path = os.path.join(output_dir, files[0])
    return file_path
"""


def create_component(username: str, component_name: str):
    """
    Dynamically create a reusable container component for the Kubeflow Pipeline steps

    :param username: Docker username to prefix to the Docker image name
    :param component_name: Name of the component, used to generate the function name and specify the Docker image
    """
    comp_name = component_name.replace('-', '_')

    # Default kfp.container_component configuration
    component_code = f"""
@dsl.container_component
def {comp_name}(input_path: str, output_path: str):
    return dsl.ContainerSpec(
        image=f'{username}/{component_name}:latest',
        command=['python', 'main.py'],
        args=[
            '-i', input_path, '-o', output_path
        ]
    )
    """
    # Execute the generated code to define the component function dynamically
    exec(component_code, globals())


def setup_component(component_name: str, input_path: str, output_dir: str, pvc_name: str):
    """
    Set up a component for the pipeline with various configurations (including input and output paths, and PVC mounting),
    by retrieving the dynamically created component function.
    If needed, the method can be extended to include more configurations based on the Kubeflow pipeline requirements.

    :param name: Name of the component to be included in the pipeline
    :param input_path: Path to the input file for the component
    :param output_dir: Output directory for the component's results
    :param pvc_name: Name of the Persistent Volume Claim (PVC) to be mounted
    :return: Configured component operation for the pipeline
    """
    comp_func = globals().get(component_name.replace('-', '_'))
    component_op = comp_func(input_path=input_path, output_path=output_dir)
    component_op = mount_pvc(component_op, pvc_name=pvc_name, mount_path='/mnt/data')
    # Caching can be enabled or disabled here for a specific component, if needed.
    # component_op.set_caching_options(False)
    return component_op


def generate_pipeline(username: str, dag_components: list, dag_dependencies: list, init_input: str):
    """
    Dynamically generate a Kubeflow Pipeline based on the DAG configuration. This involves creating container
    components for each step in the pipeline and setting up their execution order based on dependencies.

    :param username: Docker username for Docker image naming
    :param dag_components: List of components defined in the DAG configuration file
    :param dag_dependencies: List of dependencies defined in the DAG configuration file
    :param init_input: Name of the initial input media file path
    :return: The Kubeflow Pipeline function
    """
    for component in dag_components:
        create_component(username, component)
    create_component(username, 'save-media')

    @dsl.pipeline(
        name="Kubeflow Autopipe",
        description="Automatically generated pipeline based on the provided configuration file"
    )
    def dynamic_pipeline(pvc_name: str):
        base_mount = "/mnt/data"
        component_op = {}
        input_path = init_input

        # Set up the save_media component as first component
        output_dir = f"{base_mount}/"
        component_op['save-media'] = setup_component('save-media', input_path, output_dir, pvc_name)

        # Set up the other components based on dependencies
        for dependency in dag_dependencies:
            this_component, next_component, _ = dependency

            if this_component not in component_op:
                output_dir_this = f"{base_mount}/{this_component}"
                input_path = f"{base_mount}/{init_input}"
                component_op[this_component] = setup_component(this_component, input_path, output_dir_this, pvc_name)
                component_op[this_component].after(component_op['save-media'])

            if next_component not in component_op:
                output_dir_next = f"{base_mount}/{next_component}"
                input_path = f"{base_mount}/{this_component}.tar.gz"
                component_op[next_component] = setup_component(next_component, input_path, output_dir_next, pvc_name)
                component_op[next_component].after(component_op[this_component])

    return dynamic_pipeline


def main(input_file: str):
    # Define the local path to store the outputs saved into the pvc
    local_path = 'output'
    # Save need data from the configuration file
    dag_components, dag_dependencies, media = load_dag_configuration(input_file)

    # Save docker_username defined in the .env file
    load_dotenv()
    docker_username = os.getenv('DOCKER_USERNAME')

    # Create the PVC for the pipeline
    pvc_name = create_pvc()

    # Save the name of the file to be used as input for the pipeline
    input_filename = os.path.basename(media)

    # Generate the pipeline function
    pipeline_func = generate_pipeline(username=docker_username, dag_components=dag_components, dag_dependencies=dag_dependencies, init_input=input_filename)
    pipeline_filename = 'pipeline.yaml'
    # Execute the pipeline
    pipeline_run(pvc_name, pipeline_func, pipeline_filename)
    time.sleep(5)

    # Download the output file from the PVC to the local machine
    download_from_pvc(pvc_name, local_path)
    # Delete the PVC after the pipeline execution
    delete_pvc(pvc_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to application_dag.yaml configuration file")
    args = vars(parser.parse_args())

    main(args['input'])
