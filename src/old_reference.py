import kfp
from kfp import dsl
from kfp import kubernetes
from kfp.kubernetes import CreatePVC, DeletePVC, mount_pvc

import uuid
import subprocess
from auth import KFPClientManager


def create_pvc():
    unique_id = str(uuid.uuid4())
    pvc_name = f"parallel-maskdetect-{unique_id}"
    pvc_yaml = f"""
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: {pvc_name}
  namespace: team-1
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi
  storageClassName: local-path
"""
    with open("pvc.yaml", "w") as file:
        file.write(pvc_yaml)
    subprocess.run(["sudo", "kubectl", "apply", "-f", "pvc.yaml"], check=True)
    return pvc_name


@dsl.container_component
def download_video(url: str, output_video: str):
    return dsl.ContainerSpec(
        image='litovn/proai_download_video:v1',
        command=['python', 'video_downloader.py'],
        args=['-u', url, '-o', output_video]
    )


@dsl.container_component
def blurry_faces(input_video: str, output_dir: str, threshold: float):
    return dsl.ContainerSpec(
        image='litovn/proai_blurry_faces:v1',
        command=['sh', '-c'],
        args=[
            f'python main.py -i {input_video} -o {output_dir} -t {threshold}'
        ]
    )


@dsl.container_component
def mask_detector(input_image_path: str, output_dir: str, confidence: float, threshold: float):
    return dsl.ContainerSpec(
        image='litovn/proai_mask_detector:v2',
        command=['sh', '-c'],
        args=[
            f'python main.py -i {input_image_path} -o {output_dir} -c {confidence} -t {threshold}'
        ]
    )


'''
def localsave_access_pvc(pvc_name):
    pvc_yaml = f"""
apiVersion: v1
kind: Pod
metadata:  
  name: access-{pvc_name}
  namespace: team-1
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
    with open("access_pvc.yaml", "w") as file:
        file.write(pvc_yaml)
    subprocess.run(["sudo", "kubectl", "apply", "-f", "access_pvc.yaml"], check=True)
    
    # Check il LOCAL_PATH folder exists
    # subprocess.run(["sudo", "kubectl", "cp", "team-1/access-{pvc_name}:/mnt/data", "{LOCAL_PATH}"], check=True)


def delete_pvc(pvc_name):
    delete_command = f"sudo kubectl delete pvc {pvc_name} --namespace=team-1"
    subprocess.run(delete_command, shell=True, check=True)
'''


@dsl.pipeline(
    name='Mask Detector Pipeline',
    description='Pipeline that downloads a video, applies blur to faces, and detects masks.'
)
def video_processing_pipeline(video_url: str, prefix: str, pvc_name: str, b_threshold: float = 0.7, m_confidence: float = 0.2, m_threshold: float = 0.1):
    base_mount = "/mnt/data"
    
    video_path = f"{base_mount}/video.mp4"
    blur_dir = f"{base_mount}/{prefix}/"
    mask_dir = f"{base_mount}/detect/"

    video_op = download_video(url=video_url, output_video=video_path)
    video_op = mount_pvc(video_op, pvc_name=pvc_name, mount_path=base_mount)
    video_op.set_caching_options(False)
    
    blurred_op = blurry_faces(input_video=video_path, output_dir=blur_dir, threshold=b_threshold).after(video_op)
    blurred_op = mount_pvc(blurred_op, pvc_name=pvc_name, mount_path=base_mount)
    blurred_op.set_caching_options(False)
    
    mask_op = mask_detector(input_image_path=base_mount, output_dir=mask_dir, confidence=m_confidence, threshold=m_threshold).after(blurred_op)
    mask_op = mount_pvc(mask_op, pvc_name=pvc_name, mount_path=base_mount)
    mask_op.set_caching_options(False)

    delete_op = DeletePVC(pvc_name=pvc_name).after(mask_op)
	
if __name__ == '__main__':
    kfp_client_manager = KFPClientManager(
        api_url="https://deploykf.example.com:8443/pipeline",
        skip_tls_verify=True,
        dex_username="user1@example.com",
        dex_password="user1",
        dex_auth_type="local"
    )
    
    client = kfp_client_manager.create_kfp_client()

    runs = [
        {'video_url': 'https://github.com/litovn/temp_repo/raw/main/long_video.mp4', 'prefix': 'run1_'},
        {'video_url': 'https://github.com/litovn/temp_repo/raw/main/long_video.mp4', 'prefix': 'run2_'},
        {'video_url': 'https://github.com/litovn/temp_repo/raw/main/long_video.mp4', 'prefix': 'run3_'},
        {'video_url': 'https://github.com/litovn/temp_repo/raw/main/long_video.mp4', 'prefix': 'run4_'},
        {'video_url': 'https://github.com/litovn/temp_repo/raw/main/long_video.mp4', 'prefix': 'run5_'}
    ]

    for run_params in runs:
        pvc_name = create_pvc()
    
        pipeline_package_path = f"pipeline_parallel_{run_params['prefix']}.yaml"
        kfp.compiler.Compiler().compile(pipeline_func=video_processing_pipeline, package_path=pipeline_package_path)
        
        run_name = f"Pipeline run for {run_params['prefix']}"
        client.create_run_from_pipeline_package(
            pipeline_file=pipeline_package_path,
            arguments={
                'video_url': run_params['video_url'],
                'prefix': run_params['prefix'],
                'pvc_name': pvc_name 
            },
            run_name=run_name,
            namespace='team-1'
        )
        
        # Optional: Save PVC content locally
        # localsave_access_pvc(pvc_name)
        
        # Optional: Delete the PVC post-run
        # delete_pvc(pvc_name)

