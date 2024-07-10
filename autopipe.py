import os
import yaml
import subprocess
import argparse
import logging

# Configure logging to display information based on your needs
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(levelname)s - %(message)s', datefmt='%H:%M:%S')


def run_script(script_path, input):
    """
    Run a script and wait for it to complete

    :param script_path: Path to the script to run
    """
    result = subprocess.run(['python3', script_path, '-i', input], capture_output=True, text=True)
    if result.returncode != 0:
        logging.error(f"Error running {script_path}: {result.stderr}")
        exit(result.returncode)
    else:
        logging.info(f"{script_path} executed successfully: {result.stdout}")


def main(input_file):
    """
    Run the kubeflow autopipe tool to build and deploy the pipeline

    :param input_file: Path to the application_dag.yaml configuration file
    """
    if not os.path.exists('output'):
        os.makedirs('output')

    with open(input_file, 'r') as file:
        config = yaml.safe_load(file)

    # 1. Save video
    logging.info("Save Video script, starting...\n")
    input_video = config['System']['input_media']
    run_script('src/save-video/main.py', input_video)

    # 2. Download components
    if 'repository' in config['System']:
        logging.info("Download Components script, starting...\n")
        run_script('download_components.py', input_file)
    else:
        logging.info("Repository not specified, skipping download components.")

    # 3. Build Docker images
    logging.info("Build Docker Image script, starting...\n")
    run_script('docker_build.py', input_file)

    # 4. Pipeline manager
    logging.info("Pipeline Manager script, starting...\n")
    run_script('src/pipeline_manager.py', input_file)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to application_dag.yaml configuration file")
    args = vars(parser.parse_args())

    main(args['input'])
