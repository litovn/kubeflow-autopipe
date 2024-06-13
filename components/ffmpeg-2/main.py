import sys
import subprocess
import os
import argparse

from aisprint.annotations import annotation


def execute_command(command):
    print(">_ " + command)
    subprocess.run(command.split())


@annotation({'component_name': {'name': 'ffmpeg-2'}})
def main(args):

    orig_input = args['input']
    orig_output = args['output']

    print("SCRIPT: Input at '{}', saving output in '{}'".format(args['input'], args['output']))

    output_dir = os.path.dirname(orig_output)
    output_name = os.path.basename(orig_output)

    temp_audio_path = orig_input.replace(".mp4", ".wav")
    output_audio_path = orig_output + ".wav"
    output_clip_path = orig_output + ".mp4"
    output_zip_path = orig_output + ".tar.gz"

    output_audio_name = output_name + ".wav"
    output_clip_name = output_name + ".mp4"
    output_zip_name = output_name + ".tar.gz"
    
    # extract audio track
    execute_command("ffmpeg -i %s -map 0:a %s" % (orig_input, temp_audio_path))

    # down-sample audio track
    execute_command("ffmpeg -i %s -vn -ar 16000 -ac 1 %s" % (temp_audio_path, output_audio_path))

    # compress video file
    execute_command("ffmpeg -i %s -vcodec libx264 -crf 30 %s" % (orig_input, output_clip_path))

    # alternative that copies the clip without compression
    # cp "$INPUT_FILE_PATH" "$TMP_OUTPUT_DIR/$INPUT_FILE"

    # repack everything, remove unzipped outputs
    os.chdir(output_dir)
    execute_command("tar -czvf %s %s %s" % (output_zip_name, output_audio_name, output_clip_name))
    execute_command("rm " + output_audio_name)
    execute_command("rm " + output_clip_name)
    
    
    # ---------------

if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", help="path to output images")
    args = vars(parser.parse_args())

    main(args)

