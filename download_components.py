import os
import shutil
import yaml
import logging
from git import Repo

temp_dir = "./repo"
components_dir = "./components"

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')


def load_dag_configuration(dag_path: str):
    """
    Load the dag configuration from the yaml file

    :param dag_path: path to the dag.yaml file
    :return: dag configuration repository and components information
    """
    with open(dag_path, 'r') as file:
        data = yaml.safe_load(file)
        return data['System']['repository'], data['System']['components']


def clone_repository(repo_url: str, local_path: str):
    """
    Clone repository to a local path. If folder already exists, overwrite it

    :param repo_url: URL of the repository to clone
    :param local_path: path to clone the repository into
    """
    if os.path.exists(local_path):
        shutil.rmtree(local_path)
    Repo.clone_from(repo_url, local_path)


def check_copy_components(src_path: str, components_path: str, components: list):
    """
    Checks for the components in the repo and copy to a 'components' folder

    :param src_path: path to the source repository
    :param components_path: path to the local components folder
    :param components: list of components names
    """
    if not os.path.exists(components_path):
        os.makedirs(components_path)

    repo_folders = os.listdir(src_path)
    missing_components = []

    # Check if the component defined in the dag exists in the repository as directory name
    # and copy it to the components folder else add it to the missing components list
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
    Removes the specified directory and all its contents

    :param path: path to the directory to delete
    """
    if os.path.exists(path):
        shutil.rmtree(path)


if __name__ == "__main__":
    config_file_path = 'application_dag.yaml'
    repo_url, components = load_dag_configuration(config_file_path)
    clone_repository(repo_url, temp_dir)
    check_copy_components(temp_dir, components_dir, components)
    clean_up(temp_dir)
