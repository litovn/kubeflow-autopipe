import os
import yaml
import logging

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
        return data['System']['components'], data['System']['dependencies']


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


def create_component(component_name: str):
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
        image=f'myapp/{component_name}:latest',
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
    component_op.set_caching_options(False)

    return component_op


def generate_pipeline(dag_components: list, dag_dependencies: list, pvc_name: str, init_input_path: str):
    """
    Create the components function, then generate the pipeline dynamically based on the DAG configuration

    :param dag_dependencies: dependencies defined in the DAG config
    :param pvc_name: name of the pvc to use for the pipeline
    :param init_input_path: path to the initial input file
    :return: pipeline function
    """
    for component in dag_components:
        create_component(component)

    @dsl.pipeline(
        name="Generated Pipeline from YAML",
        description="Automatically generated pipeline based on application_dag.yaml"
    )
    def dynamic_pipeline(video_path: str = init_input_path, pvc_name: str = pvc_name):
        base_mount = "/mnt/data"
        component_op = {}
        last_component = None
        input_path = video_path

        for dependency in dag_dependencies:
            this_component, next_component, _ = dependency

            if this_component not in component_op:
                output_dir_this = f"{base_mount}/{this_component}"
                component_op[this_component] = setup_component(this_component, input_path, output_dir_this, pvc_name)

            if next_component not in component_op:
                output_dir_next = f"{base_mount}/{next_component}"
                input_path = f"{base_mount}/{this_component}.tar.gz"
                component_op[next_component] = setup_component(next_component, input_path, output_dir_next, pvc_name)
                component_op[next_component].after(component_op[this_component])
                last_component = next_component

        delete_op = DeletePVC(pvc_name=pvc_name).after(component_op[last_component])

    return dynamic_pipeline


if __name__ == '__main__':
    video_input_path = ' '
    dag_path = ' '
    dag_components, dag_dependencies = load_dag_configuration(dag_path)

    pvc_name = create_pvc()

    pipeline_func = generate_pipeline(dag_components=dag_components, dag_dependencies=dag_dependencies, pvc_name=pvc_name, init_input_path=video_input_path)
    pipeline_filename = 'pipeline.yaml'

    pipeline_run(video_input_path, pvc_name, pipeline_func, pipeline_filename)

    local_path = ' '
    # download_from_pvc(pvc_name, local_path)
    # delete_pvc(pvc_name)
