import os
import yaml
import logging

import kfp
from kfp import dsl
from kfp.kubernetes import mount_pvc

from pvc_manager import *
from pipeline_run import *

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def load_dag_configuration(dag_path):
    """
    Load the dag configuration from the yaml file

    :param dag_path: path to the dag.yaml file
    :return: dag configuration
    """
    with open(dag_path, 'r') as file:
        return yaml.safe_load(file)


def scan_dir(directory):
    """
    Search for all files in the given directory and remember its path

    :param directory: directory to scan
    :return: list of all the paths of files in the given directory
    """
    file_path = []

    if not os.path.exists(directory):
        logging.error(f"The directory {directory} does not exist.")

    for file in os.listdir(directory):
        full_path = os.path.join(directory, file)
        if os.path.isfile(full_path):
            file_path.append(full_path)

    return file_path


def setup_op(component_name, component_dir, base_mount, pvc_name):
    """
    Set-up operation function to handle dynamic input file and component execution

    :param component_name: name of the component
    :param component_dir: output directory of the previous component
    :param base_mount: base mount point
    :param pvc_name: name of the pvc
    :return: component_op
    """
    input_files = scan_dir(component_dir)
    # TODO: da gestire anche output multipli
    input_file = input_files[0]

    output_dir = f"{base_mount}/{component_name}/"

    component_op = create_component(component_name, input_file, output_dir)
    component_op = mount_pvc(component_op, pvc_name=pvc_name, mount_path=output_dir)
    component_op.set_caching_options(False)

    return component_op


def create_component(component_name: str, input_file: str, output_dir: str):
    """
    Creation of a reusable container component for the various pipeline steps

    :param component_name: name of the component
    :param input_file: input file
    :param output_dir: output directory
    :return: the container component to be used in the pipeline
    """
    # Default kfp container component configuration
    @dsl.container_component
    def component_func(input_path: str = input_file, output_path: str = output_dir):
        return dsl.ContainerSpec(
            image=f'myapp/{component_name}:latest',
            command=['sh', '-c'],
            args=[
                f'python main.py -i {input_path} -o {output_path}'
            ]
        )
    component_func.__name__ = str(component_name)
    return component_func


def generate_pipeline(dag: str, pvc_name: str, init_input_path: str):
    """
    Generate the pipeline dynamically based on the DAG configuration

    :param dag: DAG configuration
    :param pvc_name: name of the pvc to use for the pipeline
    :param init_input_path: path to the initial input file
    :return: pipeline function
    """
    @dsl.pipeline(
        name="Generated Pipeline from YAML",
        description="Automatically generated pipeline based on application_dag.yaml"
    )
    def dynamic_pipeline(init_path: str = init_input_path):
        pipe = {}
        first_component = True
        base_mount = "/mnt/data"

        for dependency in dag['System']['dependencies']:
            this_component, next_component, _ = dependency

            if first_component:
                init_output_dir = f"{base_mount}/{this_component}/"

                component_op = create_component(this_component, init_path, init_output_dir)
                component_op = mount_pvc(component_op, pvc_name=pvc_name, mount_path=init_output_dir)
                component_op.set_caching_options(False)

                pipe[this_component] = component_op
                prev_output_dir = init_output_dir
                first_component = False
            else:
                pipe[next_component] = setup_op(next_component, prev_output_dir, base_mount, pvc_name)
                prev_output_dir = f"{base_mount}/{next_component}/"

    return dynamic_pipeline


if __name__ == '__main__':
    video_input_path = '/home/proai/PycharmProjects/kubeflow-autopipe/video/input_10sec.mp4'
    dag_path = '/home/proai/PycharmProjects/kubeflow-autopipe/application_dag.yaml'
    dag_config = load_dag_configuration(dag_path)

    pvc_name = create_pvc()

    pipeline_func = generate_pipeline(dag=dag_config, pvc_name=pvc_name, init_input_path=video_input_path)
    pipeline_filename = 'pipeline.yaml'

    pipeline_run(video_input_path, pvc_name, pipeline_func, pipeline_filename)

    local_path = '/home/proai/PycharmProjects/kubeflow-autopipe/output'
    download_from_pvc(pvc_name, local_path)
    delete_pvc(pvc_name)

