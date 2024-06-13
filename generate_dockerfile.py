import os
import yaml
import subprocess


def generate_dockerfile(component, template_path, base_dir_path):
    """
    Generate Dockerfile for a given component, using the dockerfile.template
    :param component: component name to generate dockerfile for
    :param template_path: path to the dockerfile.template
    :param base_path: base path where component directories are located
    """
    # Create the needed paths for the component
    component_path = os.path.join(base_dir_path, component)
    dockerfile_path = os.path.join(component_path, 'Dockerfile')

    # Read the Dockerfile template and write to the component's directory
    with open(template_path, 'r') as template_file:
        template = template_file.read()
    with open(dockerfile_path, 'w') as dockerfile:
        dockerfile.write(template)

    # Build the Docker image
    tag = f"myapp/{component}:latest"
    build_command = ["docker", "build", "-t", tag, "."]
    result = subprocess.run(build_command, cwd=component_path, capture_output=True, text=True)

    if result.returncode == 0:
        print(f"[docker_generate]: Docker image for {component} built successfully.")
    else:
        print(f"[docker_generate]: Failed to build Docker image for {component}: {result.stderr}")

    return result


if __name__ == '__main__':
    # Load the application DAG from the YAML file
    with open('application_dag.yaml', 'r') as dag_file:
        app_dag = yaml.safe_load(dag_file)

    # Define the paths
    base_dir_path = 'components'
    template_path = 'src/dockerfile.template'

    # Generate Dockerfiles for each component
    for component in app_dag['System']['components']:
        generate_dockerfile(component, template_path, base_dir_path)
