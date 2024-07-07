import uuid
import time
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s', datefmt='%H:%M:%S')

NAMESPACE = 'team-1'


def create_pvc(storage_size: str = '5Gi'):
    """
    Creates a Kubernetes PersistentVolumeClaim with a unique UUID to ensure it does not collide with existing PVC names
    The PVC is configured with the specifications used by DeployKF

    :param storage_size: Storage size for the PVC, defaults to '5Gi'
    :return: The unique name of the created PVC
    """
    unique_id = str(uuid.uuid4())
    pvc_name = f"pipe-pvc-{unique_id}"
    # Default yaml template to create a PVC
    pvc_yaml = f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {pvc_name}
  namespace: {NAMESPACE}
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: {storage_size}
  storageClassName: local-path
"""
    # Create the defined PVC to your local machine
    with subprocess.Popen(["kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        stdout, stderr = process.communicate(input=pvc_yaml)
        if process.returncode != 0:
            logging.error(f"Failed to create PVC: {stderr}")
            return None

    logging.info(f"PVC {pvc_name} created successfully")
    return str(pvc_name)


def download_from_pvc(pvc_name: str, local_path: str):
    """
    Creates a Kubernetes temporary Pod to access the PVC where the files from the pipeline run are stored and download
    to a given local path

    :param pvc_name: The name of the PVC to download content from
    :param local_path: The local path where you want to store the downloaded file
    """
    # yaml definition to create a Pod with the desired PVC attached to it
    pvc_yaml = f"""
apiVersion: v1
kind: Pod
metadata:  
  name: pvc-access-pod
  namespace: {NAMESPACE}
spec:
  containers:  
  - name: pvc-access-container
    image: busybox    
    volumeMounts:
    - mountPath: "/mnt/data"      
      name: pvc-vol
    command: ["sleep", "3600"]  
  volumes:
  - name: pvc-vol    
    persistentVolumeClaim:
      claimName: {pvc_name}
"""
    # Create the defined Pod
    with subprocess.Popen(["kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
        stdout, stderr = process.communicate(input=pvc_yaml)
        if process.returncode != 0:
            logging.error(f"Failed to create Pod: {stderr}")
            return

    logging.info("Pod created successfully. Proceeding with file copy...")
    time.sleep(10)

    # Copy the contents from the PVC to a defined path
    cp_command = ["kubectl", "cp", f"{NAMESPACE}/pvc-access-pod:/mnt/data", local_path]
    cp_process = subprocess.run(cp_command, capture_output=True, text=True)
    if cp_process.returncode == 0:
        logging.info("Files copied successfully")
    else:
        logging.error(f"Error copying files: {cp_process.stderr}")

    # Delete the defined Pod
    rm_command = ["kubectl", "delete", "pod", "pvc-access-pod", "-n", NAMESPACE]
    rm_process = subprocess.run(rm_command, capture_output=True, text=True)
    if rm_process.returncode == 0:
        logging.info("Temporary pod deleted successfully")
    else:
        logging.error(f"Error deleting pod 'pvc-access-pod': {rm_process.stderr}")


def delete_pvc(pvc_name: str):
    """
    Deletes a specified Kubernetes PersistentVolumeClaim

    :param pvc_name: The name of the PVC to delete
    :return: True if the PVC was deleted successfully, False otherwise
    """
    # Delete the defined PVC
    delete_command = ["kubectl", "delete", "pvc", pvc_name, "-n", NAMESPACE]
    result = subprocess.run(delete_command, capture_output=True, text=True)

    if result.returncode == 0:
        logging.info(f"PVC {pvc_name} deleted successfully")
    else:
        logging.error(f"Failed to delete PVC: {result.stderr}")