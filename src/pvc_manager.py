import uuid
import subprocess

NAMESPACE = 'team-1'


def create_pvc():
    """
    Creates a Kubernetes PersistentVolumeClaim with a unique UUID to ensure it does not collide with existing PVC names
    The PVC is configured with the specifications used by DeployKF
    - Storage Request: 5Gi, can be adjusted to needs

    :return: The unique name of the created PVC
    """
    unique_id = str(uuid.uuid4())
    pvc_name = f"parallel-maskdetect-{unique_id}"

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
      storage: 5Gi
  storageClassName: local-path
"""
    process = subprocess.Popen(["sudo", "kubectl", "apply", "-f", "-"], stdin=subprocess.PIPE, text=True)
    process.communicate(input=pvc_yaml)
    return pvc_name


def delete_pvc(pvc_name: str):
    """
    Deletes a specified Kubernetes PersistentVolumeClaim

    :param pvc_name: The name of the PVC to delete
    :return: True if the PVC was deleted successfully, False otherwise
    """
    delete_command = ["sudo", "kubectl", "delete", "pvc", pvc_name, "-n", NAMESPACE]
    result = subprocess.run(delete_command, capture_output=True, text=True)

    if result.returncode == 0:
        return True
    else:
        return False
