<div align="center">
  <picture>
    <img alt="KubeflowAutopipe Logo" src="https://github.com/user-attachments/assets/6ad88b68-c2fe-4b46-aaf6-35a8193bc527" width="340">
  </picture>
</div>

## Sections
- [About](#about)
- [Requirements](#requirements)
- [Execution Order](#execution-order)
- [Used Conventions](#used-conventions)
- [Configuration](#configuration)
- [Getting Started](#getting-started)
    - [deployKF](#i-setup-deploykf)
    - [Kubeflow Autopipe](#ii-setup-kubeflow-autopipe)
- [Features](#features)
- [License](#license)
- [Acknowledgments](#acknowledgments)


## About
***Kubeflow Autopipe*** is a pipeline tool designed to streamline the process of media processing and analysis by leveraging the power of [Kubeflow Pipeline](https://www.kubeflow.org/docs/components/pipelines/) components, addressing each stage in the ML lifecycle. This tool help with the orchestration of a series of components to automate the workflow of component processing, from initial ingestion through various transformations and analysis, to final output.

To achieve this automation, ***Kubeflow Autopipe*** utilizes a modular component system, allowing users to define a sequence of components and their dependencies through a configuration file. This flexibility enables users to customize the pipeline according to their specific requirements, making it easy to adapt the pipeline to different use cases.

<details>
<summary> <b><i>Kubeflow Autopipe</i></b> was written for the purpose of being tested and run on a <b>local</b> Kubernetes cluster, with the help of - 
<a href="https://www.deploykf.org/"><img src='https://raw.githubusercontent.com/deployKF/website/main/overrides/.icons/custom/deploykf-color.svg' width='12'> deployKF</a>
</summary>

>When deploying AI and ML based workloads on a cluster, you need to install several tools separately to get the job done. With Kubeflow a collection of Kustomize manifests requires significant manual patching to use in production. <br /> 
> To avoid this manual process we will install all the necessary tools on our cluster with one stack, by using [deployKF](https://www.deploykf.org/). 
> Much like Kubeflow, deployKF gives you a collection of resources to deploy on your Kubernetes cluster to ensure that you have everything you need to begin pipelining. The biggest difference conceptually is that deployKF combines Kubeflow with a few other tools, into a [centralized config system](https://www.deploykf.org/guides/values/) to manage all aspects of the platform, making the entirety of managing the cluster from an AI and ML perspective a bit easier.<br /><br />
> ***Kubeflow Autopipe*** bases the execution of its pipeline on the default values setup by deployKF and provided in the [Local Quickstart](https://www.deploykf.org/guides/local-quickstart/) guide. If you decide to modify the manually created `deploykf-app-of-apps` or `credentials` for the deployKF dashboard, make sure to apply those changes to Kubeflow Autopipe.  <br /><br />
> **Note:** Kubeflow Autopipe is not a finish product and the deployKF project is still in its early stages, so there may be some bugs or issues that need to be resolved. If you encounter any issues, please report them on the [current GitHub page](https://github.com/litovn/kubeflow-autopipe/issues).
</details>

**Note:** In Kubeflow Pipelines, you typically use container images hosted in a container registry, such as Docker Hub or Google Container Registry (GCR). This is because the Kubernetes cluster running the pipeline needs to pull the container image, and it generally cannot access images stored only locally on your machine. 

For this purpose a `.env` file was provided to set your credentials. ***Kubeflow Autopipe*** considers [Docker Hub](https://hub.docker.com/) as the chosen registry.

## Requirements
Resource | Minimum Requirement
--- | --- 
CPU Cores | `4`
RAM | `16 GB`
Storage | `64 GB`


You will need to install the following dependencies:
- Docker Engine
- [`requirements.txt`](requirements.txt) packages
- deployKF dependencies


## Execution Order
By running the [`autopipe.py`](autopipe.py) script in the main folder, the pipeline will be executed in the following order:
1. [`save_media`](src/save-media/main.py) to copy the media file to be used as input to the pipeline, from the defined local path into the `save-media` folder that will be containerized and used as the first component to save the media into a Persistent Volume Container (PVC) when the pipeline will be executed. 
<br /><br />
2. [`download_components`](download_components.py) to download the components from the defined Git repository in the config file, into the `components` folder.
   1. **Read `application_dag.yaml`**: if defined, else skip download of components
   2. **Clone Repository**: Clones the repository containing the components into a temporary folder
   3. **Copy Components**: Copies the components from the temporary folder to the `components` folder
   4. **Remove Temporary Folder**: Removes the temporary folder where the repository was cloned
<br /><br />
3. [`docker_build`](docker_build.py) to build the Docker images for each component in the `components` folder.
   1. **Read `application_dag.yaml`**: to get the names of the components
   2. **Login to Docker** 
   3. **Add Dockerfile**: Add an universal Dockerfile defined in `src/template/dockerfile.template` to each component folder
   4. **Build Docker Images**: Build the Docker images for each component
   5. **Push Docker Images**: Push the Docker images to the Docker Hub registry (other registries can be used)
   6. **Remove Untagged Images**: Remove unused Docker images from the local machine
<br /><br />
4. [`pipeline_manager`](src/pipeline_manager.py) to create and execute the pipeline in the Kubeflow environment.
   1. **Read `application_dag.yaml`**: to get the names of the components, their dependencies and the name of the input media
   2. **Create PVC**: Create a Persistent Volume Container (PVC), with a unique name, to store the input media
   3. **Create Pipeline**: Create the Kubeflow pipeline function and file to be executed, by defining the sequence of components in order of their dependencies
   4. **Execute Pipeline**: Execute the pipeline in the Kubeflow environment, by running its function and file
   5. **Download Output**: Download the outputs of all the pipeline components from the PVC to the local machine  
   6. **Delete PVC**: Delete the PVC used to store the input media

## Used Conventions

**IMPORTANT:** As of how [`pipeline_manager`](src/pipeline_manager.py) is defined now, by using Persistent Volumes you save the output of each component and pass it to the next one, it takes into consideration that the output of each component is saved following this specific convention:
```python
output_file_name = os.path.basename(output_path_dir)
output_file_name + ".tar.gz"
``` 
***Kubeflow Autopipe*** does not extract the `output_file_name` path saved by the previous component (independently of the file's name) and use it as the input for the next component automatically, because it would imply to create and updated a generic pod after each component is run by overwriting the previous one, which is not an optimal approach. 


## Configuration
The pipeline's behavior is configured through the [`application_dag.yaml`](application_dag.yaml) file. This YAML file defines the system's name, the Git repository where the component are located, the local path of the media to be used as input in the pipeline, the components name involved in the processing, and the dependencies between these components.
```yaml
System:
  name: my_new_app           
  repository: link to the repository where the components are located    # optional
  input_media: local path to the input media file to be processed
  components: ['component-name-1', 'component-name-2', ...]              # does not have to be in order
  dependencies: [['component-name-1', 'component-name-2', 1], ...]       # from component-name-1 to component-name-2, p=1
```

## Getting Started
To get started with ***Kubeflow Autopipe***, follow these steps:

### i. Setup deployKF
1. **Install deployKF**:
   <br /> Follow the instructions in the [deployKF Local Quickstart](https://www.deploykf.org/guides/local-quickstart/) guide to set up deployKF on your local Kubernetes cluster.
   <br /> If already installed, ensure that the deployKF dashboard is up and running by port-forwarding the gateway.
2. **Access the deployKF Dashboard**:
   <br /> Ensure that the deployKF dashboard is functional and are able to access the Kubeflow Pipelines UI.

### ii. Setup Kubeflow Autopipe
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/litovn/kubeflow-autopipe.git
   ```
2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Set Up Your Environment**:
   <br /> Ensure you have Docker installed and configured. Use the provided `.env` file to set your Docker credentials.
    ```
    REGISTER_USERNAME = ' '
    REGISTER_PASSWORD = ' '
    ```
4. **Configure the Pipeline**:
   <br /> Edit the `application_dag.yaml` file to customize the pipeline according to your needs. Specify the link to the Git repository where the component are located (if installation needed), the local path of the media to be used as input in the pipeline, the components name involved in the processing, and the dependencies between these components. Check [configuration](#configuration) for the structure of the configuration YAML file.
 <br /><br />
5. **Run the Pipeline**:
   <br /> Execution of **Kubeflow Autopipe**'s script, defined in [execution order](#execution-order), by running 
   ```
   python3 autopipe.py -i path_to_dag_yaml
   ```

## Features
- **Automated Media Processing Pipeline**: Simplifies the process of media processing by automating the workflow through a predefined sequence of components.
- **Modular Component System**: Utilizes a series of components defined by the user.
- **Flexible Workflow Configuration**: Allows for easy customization of the pipeline through the `application_dag.yaml` configuration file, enabling users to define their own sequence of components and dependencies.
- **Docker Image Building**: Automatically builds Docker images for each component in the pipeline, ensuring that the components are containerized and ready for execution. Docker Hub registry synchronization is also supported.
- **Kubeflow Pipeline Execution**: Executes the pipeline in the Kubeflow environment, orchestrating the sequence of components and managing the workflow.
- **Persistent Volume Container (PVC) Support**: Utilizes PVCs to store input media and output files, ensuring data persistence and efficient data management.
- **Dex Static Credentials**: Supports the use of static credentials from both inside and outside the cluster without needing user interaction during authentication with the Dex identity provider, ensuring secure access to the Kubeflow environment.
- **Large File Support**: Integrates with Git LFS to handle large files such as ONNX models, PBMM files, and scorer files, ensuring efficient management and versioning of large assets.

## License
This project is open-sourced under the MIT License. See the LICENSE file for more details.


## Acknowledgments
This project leverages the powerful features of Kubeflow, deployKF, Docker, and various open-source tools. Special thanks to the developers and contributors of these projects.
