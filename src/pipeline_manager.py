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
    :return: dag configuration components and dependencies information
    """
    with open(dag_path, 'r') as file:
        data = yaml.safe_load(file)
        return data['System']['dependencies']


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
    input_file = input_files[0]

    output_dir = f"{base_mount}/{component_name}/"

    component_op = create_component(component_name, input_file, output_dir)
    component_op = mount_pvc(component_op, pvc_name=pvc_name, mount_path=output_dir)
    component_op.set_caching_options(False)

    return component_op

'''
def create_component(component_name: str):
    """
    Creation of a reusable container component for the various pipeline steps

    :param component_name: name of the component
    :return: the container component to be used in the pipeline
    """
    # Default kfp container component configuration
    component_yaml = f"""
kind: ComponentSpec
metadata:
  name: {component_name}
implementation:
  container:
    image: myapp/{component_name}:latest
    command:
    - python
    - main.py
    args:
    - --input_path
    - '{{inputs.parameters.input_path}}'
    - --output_path
    - '{{outputs.parameters.output_path}}'
inputs:
  - {{name: input_path, type: String}}
outputs:
  - {{name: output_path, type: String}}
        """
    # Execute dynamically the component code
    return load_component_from_text(component_yaml)
''' # Non va bene, ritorna YamlComponent

def create_component(component_name: str):
    """
    Creation of a reusable container component for the various pipeline steps

    :param component_name: name of the component
    :return: the container component to be used in the pipeline
    """
    # Default kfp container component configuration
    component_code = f"""
@dsl.container_component
def {component_name}(input_path: str, output_path: str):
    return dsl.ContainerSpec(
        image=f'myapp/{component_name}:latest',
        command=['sh', '-c'],
        args=[
            'python main.py -i ' + input_path + ' -o ' + output_path
        ]
    )
    """
    # Execute dynamically the component code
    exec(component_code, globals())


def generate_pipeline(dag_dependencies: list, pvc_name: str, init_input_path: str):
    """
    Generate the pipeline dynamically based on the DAG configuration

    :param dag_dependencies: dependencies defined in the DAG config
    :param pvc_name: name of the pvc to use for the pipeline
    :param init_input_path: path to the initial input file
    :return: pipeline function
    """
    @dsl.pipeline(
        name="Generated Pipeline from YAML",
        description="Automatically generated pipeline based on application_dag.yaml"
    )
    def dynamic_pipeline(init_path: str = init_input_path):
        first_component = True
        base_mount = "/mnt/data"
        component_ops = {}

        for dependency in dag_dependencies:
            this_component, next_component, _ = dependency

            # Define the first component
            if first_component:
                output_dir = f"{base_mount}/{this_component}/"
                component_op = create_component(this_component)
                component_op = mount_pvc(component_op, pvc_name=pvc_name, mount_path=output_dir)
                component_op.set_caching_options(False)
                component_ops[this_component] = component_op
                prev_component = this_component
                first_component = False

            # Ensure next_component is defined and properly linked
            if next_component not in component_ops:
                output_dir = f"{base_mount}/{next_component}/"
                component_op = create_component(next_component)
                component_op = mount_pvc(component_op, pvc_name=pvc_name, mount_path=output_dir)
                component_op.set_caching_options(False)
                component_ops[next_component] = component_op

            # Link this component to the next component
            component_ops[next_component].after(component_ops[prev_component])
            prev_component = next_component

    return dynamic_pipeline


if __name__ == '__main__':
    video_input_path = '/home/proai/PycharmProjects/kubeflow-autopipe/video/input_10sec.mp4'
    dag_path = "C:/Users/Nikil/PycharmProjects/kubeflow-autopipe/application_dag.yaml"
    dag_dependencies = load_dag_configuration(dag_path)

    pvc_name = create_pvc()

    pipeline_func = generate_pipeline(dag_dependencies=dag_dependencies, pvc_name=pvc_name, init_input_path=video_input_path)
    pipeline_filename = 'pipeline.yaml'

    pipeline_run(video_input_path, pvc_name, pipeline_func, pipeline_filename)

    local_path = '/home/proai/PycharmProjects/kubeflow-autopipe/output'
    download_from_pvc(pvc_name, local_path)
    delete_pvc(pvc_name)

