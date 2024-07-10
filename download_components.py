import os
import shutil
import yaml
import logging
from git import Repo

# Temporary directory for cloning the repository
temp_dir = "./repo"
# Directory name where components will be stored
components_dir = "./component"
# Configure logging to display information based on your needs
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def load_dag_configuration(dag_path: str):
    """
    Load the yaml dag configuration file, to extract the required information

    :param dag_path: The file path to the YAML configuration file
    :return: A tuple containing the repository URL and a list of component names
    """
    with open(dag_path, 'r') as file:
        data = yaml.safe_load(file)
        return data['System']['repository'], data['System']['components']


def clone_repository(repo_url: str, local_path: str):
    """
    Clone a Git repository to a defined local path. If folder already exists, delete it to ensure a fresh clone of the repository

    :param repo_url: URL of the Git repository to clone
    :param local_path: The defined local path where the repository should be cloned
    """
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    Repo.clone_from(repo_url, local_path)


def check_copy_components(src_path: str, components_path: str, components: list):
    """
    Check for specified components within a cloned repository and copy them to the defined 'components' directory.
    If a component does not exist in the repository, it is noted in a list of missing components.

    :param src_path: The path to the cloned source Git repository
    :param components_path: The path to the directory where components should be copied
    :param components: List of component names to check for and copy
    """
    if not os.path.exists(components_path):
        os.makedirs(components_path)

    repo_folders = os.listdir(src_path)
    missing_components = []

    for component in components:
        if component in repo_folders and os.path.isdir(os.path.join(src_path, component)):
            src = os.path.join(src_path, component)
            dest = os.path.join(components_path, component)
            if os.path.exists(dest):
                shutil.rmtree(dest)
            shutil.copytree(src, dest)
        else:
            missing_components.append(component)

    if missing_components:
        logging.error("Failed adding components, missing components in the repository:", missing_components)
    else:
        logging.info("All components have been successfully added to the components folder")


def clean_up(path: str):
    """
    Remove a specified directory and all of its contents.
    Used to clean-up temporary directories or cloned repositories, after their contents have been processed.

    :param path: The path to the directory to delete
    """
    if os.path.exists(path):
        shutil.rmtree(path)


if __name__ == "__main__":
    config_file_path = 'application_dag.yaml'
    repo_url, components = load_dag_configuration(config_file_path)
    clone_repository(repo_url, temp_dir)
    check_copy_components(temp_dir, components_dir, components)
    clean_up(temp_dir)
