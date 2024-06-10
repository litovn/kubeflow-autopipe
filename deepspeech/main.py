import sys
import subprocess
import os
import argparse

from aisprint.annotations import annotation


def execute_command(command):
    print(">_ " + command)
    subprocess.run(command.split())


def get_command_output(command):
    print(">_ " + command)
    return subprocess.run(command.split(), capture_output=True)


@annotation({'component_name': {'name': 'deepspeech'}})
def main(args):

    orig_input = args['input']
    orig_output = args['output']

    print("SCRIPT: Input at '{}', saving output in '{}'".format(args['input'], args['output']))

    input_dir = os.path.dirname(orig_input)
    output_dir = os.path.dirname(orig_output)
    output_name = os.path.basename(orig_output)

    archive_name = output_name + ".tar.gz"
    video_name = output_name + ".mp4"
    video_path = os.path.join(output_dir, video_name)
    
    command = "tar -xvzf %s -C %s" % (orig_input, input_dir)
    execute_command(command)
    
    model = "deepspeech-0.9.3-models.pbmm"
    scorer = "deepspeech-0.9.3-models.scorer"
    audio_path = orig_input.replace(".tar.gz", ".wav")

    command = "deepspeech --model %s --scorer %s --audio %s" % (model, scorer, audio_path)
    output = get_command_output(command)
    print(output.stdout.decode('utf-8'))
    
    with open(os.path.join(output_dir, "transcript.txt"), "w") as file:
        file.write(output.stdout.decode('utf-8'))

    execute_command("cp %s %s" % (orig_input.replace(".tar.gz", ".mp4"), video_path))
    os.chdir(output_dir)
    execute_command("tar -czvf %s %s %s" % (archive_name, video_name, "transcript.txt"))
    execute_command("rm " + video_name)
    execute_command("rm " + "transcript.txt")
    
    # ---------------


if __name__ == '__main__':
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", help="path to output images")
    args = vars(parser.parse_args())

    main(args)

