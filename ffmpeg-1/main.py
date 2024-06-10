import sys
import subprocess
import os
import argparse

from aisprint.annotations import annotation


def execute_command(command):
    print(">_ " + command)
    subprocess.run(command.split())


@annotation({'component_name': {'name': 'ffmpeg-1'}})
def main(args):

    orig_input = args['input']
    orig_output = args['output']

    print("SCRIPT: Input at '{}', saving output in '{}'".format(args['input'], args['output']))

    input_dir = os.path.dirname(orig_input)
    output_dir = os.path.dirname(orig_output)
    output_name = os.path.basename(orig_output)
    
    command = "tar -xvzf %s -C %s" % (orig_input, output_dir)
    execute_command(command)
    
    timestamp_path = os.path.join(output_dir, "timestamps.txt")
    video_path = os.path.join(output_dir, "video.mp4")
    
    with open(timestamp_path) as file:
        lines = file.readlines()

    for i in range(len(lines)):
        line = lines[i]
        start, end = line.split()

        clip_path = orig_output + "_" + str(i) + ".mp4"
        
        command = "ffmpeg -ss %s -to %s -i %s -c copy %s" % (start, end, video_path, clip_path)
        execute_command(command)

    execute_command("rm " + timestamp_path)
    execute_command("rm " + video_path)    
    
    # ---------------

if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", help="path to output images")
    args = vars(parser.parse_args())

    main(args)

