import os
import yaml
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def cleanup_untagged_images():
    """
    Removes untagged Docker images from local machine
    """
    remove_command = ["docker", "image", "prune", "-f"]
    result = subprocess.run(remove_command, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info("Successfully removed untagged images")
    else:
        logging.error(f"Error removing untagged images: {result.stderr}")


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
    if not os.path.exists(template_path):
        logging.error(f"Template path '{template_path}' does not exist")
        return

    # Read the Dockerfile template and write to the component's dir
    with open(template_path, 'r') as template_file:
        template = template_file.read()
    with open(dockerfile_path, 'w') as dockerfile:
        dockerfile.write(template)

    # Build the Docker Image
    tag = f"myapp/{component}:latest"
    build_command = ["docker", "build", "-t", tag, "."]
    result = subprocess.run(build_command, cwd=component_path, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info(f"Docker image for {component} built successfully")
    else:
        logging.error(f"Failed to build Docker image for {component}: {result.stderr}")


def main(base_dir_path: str, template_path: str):
    logging.info("Welcome to the Docker image generator, application starting...\n")
    # Base the container creation on the components defined in the dag
    with open('application_dag.yaml', 'r') as dag_file:
        app_dag = yaml.safe_load(dag_file)
    # Generate Dockerfile for each component
    for component in app_dag['System']['components']:
        generate_dockerfile(component, template_path, base_dir_path)
    # Remove unused local docker images
    cleanup_untagged_images()


if __name__ == '__main__':
    # Define paths
    base_dir_path = 'components'
    template_path = 'src/template/dockerfile.template'
    main(base_dir_path, template_path)
