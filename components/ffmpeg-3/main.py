import sys
import subprocess
import os
import argparse

from aisprint.annotations import annotation


def execute_command(command):
    print(">_ " + command)
    subprocess.run(command.split())


@annotation({'component_name': {'name': 'ffmpeg-3'}})
def main(args):

    orig_input = args['input']
    orig_output = args['output']

    print("SCRIPT: Input at '{}', saving output in '{}'".format(args['input'], args['output']))

    input_dir = os.path.dirname(orig_input)
    output_dir = os.path.dirname(orig_output)
    output_name = os.path.basename(orig_output)

    video_path = orig_input.replace(".tar.gz", ".mp4")
    
    command = "tar -xvzf %s -C %s" % (orig_input, input_dir)
    execute_command(command)

    command = "ffmpeg -i %s -vf fps=12/60 %s" % (video_path, orig_output + "-%d.jpg")
    execute_command(command)    
    
    # ---------------

if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", help="path to output images")
    args = vars(parser.parse_args())

    main(args)

