import os
import yaml
import subprocess
import logging
from dotenv import load_dotenv
from kfp import dsl
from kfp.kubernetes import mount_pvc, DeletePVC

from kube.pvc_manager import *
from kube.pipeline_run import *


logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def load_dag_configuration(dag_path):
    """
    Load the dag configuration from the yaml file

    :param dag_path: path to the dag.yaml file
    :return: dag configuration components and dependencies information
    """
    with open(dag_path, 'r') as file:
        data = yaml.safe_load(file)
        return data['System']['components'], data['System']['dependencies'], data['System']['input_media']


# With download_from_pvc method defined in pvc_manager.py, it might be possible to search for the output file path
# saved by the previous component (independently of its name) in the PVC and download it to the local machine, then
# use it as the input for the next component.
# This method is not used, because it would imply to create an updated pod after each component by overwriting the
# previous one, which is not an optimal approach.
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
    Creation of a reusable container component for the various pipeline steps

    :param component_name: name of the component
    :return: the container component to be used in the pipeline
    """
    comp_name = component_name.replace('-', '_')

    # Default kfp container component configuration
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
    # To execute dynamically the component
    exec(component_code, globals())


def setup_component(component_name: str, input_path: str, output_dir: str, pvc_name: str):
    """
    Setup the component for the pipeline with various configurations.
    If needed, the method can be extended to include more configurations based on the Kubeflow pipeline requirements.

    :param name: name of the component to be in the pipeline
    :param input_path: path to the input file for the component
    :param output_dir: output directory for the component
    :param pvc_name: name of the pvc to be mounted
    :return: component_op
    """
    comp_func = globals().get(component_name.replace('-', '_'))
    component_op = comp_func(input_path=input_path, output_path=output_dir)
    component_op = mount_pvc(component_op, pvc_name=pvc_name, mount_path='/mnt/data')
    # Caching OFF specified in the pipeline run, but can be set to True if needed for a specific component
    # component_op.set_caching_options(False)

    return component_op


def generate_pipeline(username: str, dag_components: list, dag_dependencies: list, init_input: str):
    """
    Create the components function, then generate the pipeline dynamically based on the DAG configuration

    :param dag_components: components defined in the DAG config
    :param dag_dependencies: dependencies defined in the DAG config
    :param init_input: name of the initial input file
    :return: pipeline function
    """

    for component in dag_components:
        create_component(username, component)
    create_component(username, 'save-video')

    @dsl.pipeline(
        name="Generated Pipeline from YAML",
        description="Automatically generated pipeline based on application_dag.yaml"
    )
    def dynamic_pipeline(pvc_name: str):
        base_mount = "/mnt/data"
        component_op = {}
        last_component = None
        input_path = init_input

        # Set up the save_video component as first component
        output_dir = f"{base_mount}/"
        component_op['save-video'] = setup_component('save-video', input_path, output_dir, pvc_name)

        # Set up the other components based on dependencies
        for dependency in dag_dependencies:
            this_component, next_component, _ = dependency

            if this_component not in component_op:
                output_dir_this = f"{base_mount}/{this_component}"
                input_path = f"{base_mount}/{init_input}"
                component_op[this_component] = setup_component(this_component, input_path, output_dir_this, pvc_name)
                component_op[this_component].after(component_op['save-video'])

            if next_component not in component_op:
                output_dir_next = f"{base_mount}/{next_component}"
                input_path = f"{base_mount}/{this_component}.tar.gz"
                component_op[next_component] = setup_component(next_component, input_path, output_dir_next, pvc_name)
                component_op[next_component].after(component_op[this_component])
                last_component = next_component

        delete_op = DeletePVC(pvc_name=pvc_name).after(component_op[last_component])

    return dynamic_pipeline


if __name__ == '__main__':
    dag_path = ' '

    dag_components, dag_dependencies, media = load_dag_configuration(dag_path)

    load_dotenv()
    docker_username = os.getenv('DOCKER_USERNAME')

    pvc_name = create_pvc()

    input_filename = os.path.basename(media)

    pipeline_func = generate_pipeline(username=docker_username, dag_components=dag_components, dag_dependencies=dag_dependencies, init_input=input_filename)
    pipeline_filename = 'pipeline.yaml'

    pipeline_run(pvc_name, pipeline_func, pipeline_filename)

    local_path = ' '
    download_from_pvc(pvc_name, local_path)
