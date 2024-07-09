import os
import yaml
import subprocess
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def docker_login(username, password):
    """
    Login to Docker registry

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
    :param base_dir_path: base path where component directories are located
    :return: path to the component directory
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

    :param username: Docker username
    :param component: component name
    :param component_path: path to the component directory
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
    Push Docker image to Docker Hub

    :param username: Docker username
    :param component: component name
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
    # Read credentials from .env file
    load_dotenv()
    docker_username = os.getenv('DOCKER_USERNAME')
    docker_password = os.getenv('DOCKER_PASSWORD')
    # Docker login
    docker_login(docker_username, docker_password)

    # Base the container creation on the components defined in the dag
    with open('application_dag.yaml', 'r') as dag_file:
        app_dag = yaml.safe_load(dag_file)

    # Generate container for each component
    for component in app_dag['System']['components']:
        component_path = generate_dockerfile(component, template_path, base_dir_path)
        build_docker_image(docker_username, component, component_path)
    # Generate container for save_video component
    build_docker_image(docker_username, 'save-video', 'src/save-video')

    # Push the containers to Docker Hub
    for component in app_dag['System']['components']:
        push_to_hub(docker_username, component)
    push_to_hub(docker_username, 'save-video')

    # Remove unused local docker images
    cleanup_untagged_images()


if __name__ == '__main__':
    # Define paths
    base_dir_path = 'components'
    template_path = 'src/template/dockerfile.template'
    main(base_dir_path, template_path)
