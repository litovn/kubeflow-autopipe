import sys
import subprocess
import os

import argparse

from aisprint.annotations import annotation


def execute_command(command):
    print(">_ " + command)
    subprocess.run(command.split())


@annotation({'component_name': {'name': 'ffmpeg-0'}})
def main(args):

    orig_input = args['input']
    orig_output = args['output']

    print("SCRIPT: Input at '{}', saving output in '{}'".format(args['input'], args['output']))

    output_dir = os.path.dirname(orig_output)
    output_name = os.path.basename(orig_output)

    archive_name = output_name + ".tar.gz"
    video_path = os.path.join(output_dir, "video.mp4")
    audio_path = os.path.join(output_dir, "audio.wav")
    
    execute_command("ffmpeg -i %s -map 0:a %s" % (orig_input, audio_path))
    execute_command("cp %s %s" % (orig_input, video_path))
    os.chdir(output_dir)
    execute_command("tar -czvf %s %s %s" % (archive_name, "video.mp4", "audio.wav"))
    execute_command("rm " + "video.mp4")
    execute_command("rm " + "audio.wav")
    
    # ---------------

if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", help="path to output images")
    args = vars(parser.parse_args())

    main(args)

