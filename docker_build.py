import os
import yaml
import subprocess
import logging
from dotenv import load_dotenv

# Configure logging to display information based on your needs
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def load_dag_configuration(dag_path: str):
    """
    Load the yaml dag configuration file, to extract the required information

    :param dag_path: The file path to the YAML configuration file
    :return: List of component names
    """
    with open(dag_path, 'r') as file:
        data = yaml.safe_load(file)
        return data['System']['components']


def docker_login(username, password):
    """
    Login to Docker registry using provided credentials.
    This function constructs a Docker login command using the provided username and password, then executes it.

    :param username: Docker username
    :param password: Docker password
    """
    login_command = f"echo {password} | docker login --username {username} --password-stdin"
    result = subprocess.run(login_command, shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info("Successfully logged into Docker")
    else:
        logging.error(f"Failed to login to Docker: {result.stderr}")


def cleanup_untagged_images():
    """
    Removes untagged Docker images from local machine, to help free space.
    """
    remove_command = ["docker", "image", "prune", "-f"]
    result = subprocess.run(remove_command, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info("Successfully removed untagged images")
    else:
        logging.error(f"Error removing untagged images: {result.stderr}")


def generate_dockerfile(component, template_path, base_dir_path):
    """
    Generate Dockerfile for a given component, using a specified template.

    :param component: Component name to generate Dockerfile for
    :param template_path: path to the Dockerfile template
    :param base_dir_path: Base directory path where component directories are located
    :return: Path to the directory of the component
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

    return component_path


def build_docker_image(username, component, component_path):
    """
    Build Docker image for a given component

    :param username: Docker username used for tagging the image
    :param component: Name of the component for which to build the image
    :param component_path: Path to the directory of the component
    """
    tag = f"{username}/{component}:latest"
    build_command = ["docker", "build", "-t", tag, "."]
    result = subprocess.run(build_command, cwd=component_path, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info(f"Docker image for {component} built successfully")
    else:
        logging.error(f"Failed to build Docker image for {component}: {result.stderr}")


def push_to_hub(username, component):
    """
    Push Docker image of the given component to Docker Hub

    :param username: Docker username used for tagging the image
    :param component: Name of the component for which to build the image
    """
    tag = f"{username}/{component}:latest"
    push_command = ["docker", "push", tag]
    result = subprocess.run(push_command, capture_output=True, text=True)
    if result.returncode == 0:
        logging.info(f"Successfully pushed {component} to Docker Hub")
    else:
        logging.error(f"Failed to push {component} to Docker Hub: {result.stderr}")


def main(base_dir_path: str, template_path: str):
    logging.info("Welcome to the Docker image generator, application starting...\n")
    # Load the components from the dag configuration file
    components = load_dag_configuration('application_dag.yaml')

    # Read credentials from .env file
    load_dotenv()
    docker_username = os.getenv('DOCKER_USERNAME')
    docker_password = os.getenv('DOCKER_PASSWORD')
    # Docker login
    docker_login(docker_username, docker_password)

    # Generate container for each component
    for component in components:
        component_path = generate_dockerfile(component, template_path, base_dir_path)
        build_docker_image(docker_username, component, component_path)
    # Generate container for save_video component
    build_docker_image(docker_username, 'save-video', 'src/save-video')

    # Push the containers to Docker Hub
    for component in components:
        push_to_hub(docker_username, component)
    push_to_hub(docker_username, 'save-video')

    # Remove unused local docker images
    cleanup_untagged_images()


if __name__ == '__main__':
    base_dir_path = 'components'
    template_path = 'src/template/dockerfile.template'
    main(base_dir_path, template_path)
