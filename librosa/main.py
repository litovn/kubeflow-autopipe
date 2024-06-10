import librosa
import sys
import time
import math
import os
import argparse
import subprocess

from aisprint.annotations import annotation


def execute_command(command):
    print(">_ " + command)
    subprocess.run(command.split())


def samples_to_timestamp(sample, is_start):
    time_in_seconds = sample / 22050
    if is_start:
        time_in_seconds = math.floor(time_in_seconds)
    else:
        time_in_seconds = math.ceil(time_in_seconds)
    formatted_time = time.strftime('%H:%M:%S', time.gmtime(time_in_seconds))
    return formatted_time, time_in_seconds


@annotation({'component_name': {'name': 'librosa'}})
def main(args):

    orig_input = args['input']
    orig_output = args['output']

    print("SCRIPT: Input at '{}', saving output in '{}'".format(args['input'], args['output']))

    output_dir = os.path.dirname(orig_output)
    output_name = os.path.basename(orig_output)

    video_path = os.path.join(output_dir, "video.mp4")
    audio_path = os.path.join(output_dir, "audio.wav")

    command = "tar -xvzf %s -C %s" % (orig_input, output_dir)
    execute_command(command)

    audio, sr = librosa.load(audio_path, sr=22050, mono=True)
    duration = librosa.get_duration(audio)
    
    max_sentence_lenght = 30
    min_sentence_lenght = 6

    min_clips_number = duration / max_sentence_lenght
    max_clips_number = duration / min_sentence_lenght
    
    for threshold_db in range(24, 50):
        clips = librosa.effects.split(audio, top_db=threshold_db)
        print(">_ %s clips with %s dB as treshold" % (len(clips), threshold_db))
        if len(clips) >= min_clips_number and len(clips) < max_clips_number:
            break

    with open(output_dir + "/timestamps.txt", "a") as file:
        last_timestamp = "00:00:00"
        last_seconds = 0
        for i in range(len(clips)):
            c = clips[i]
            # start = samples_to_timestamp(c[0], True)
            start_timestamp = last_timestamp
            start_seconds = last_seconds
            end_timestamp, end_seconds = samples_to_timestamp(c[1], False)
            clip_lenght = end_seconds - start_seconds
            if start_seconds != end_timestamp and clip_lenght > min_sentence_lenght:
                file.write(start_timestamp + " " + end_timestamp + "\n")
                last_timestamp = end_timestamp
                last_seconds = end_seconds

    audio_file_name = output_name + ".wav"
    video_file_name = output_name + ".mp4"

    os.chdir(output_dir)
    command = "tar -cvzf %s %s %s" % (output_name + ".tar.gz", "timestamps.txt", "video.mp4")
    execute_command(command)
    execute_command("rm " + "timestamps.txt")
    execute_command("rm " + "audio.wav")
    execute_command("rm " + "video.mp4")


if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", help="path to output images")
    args = vars(parser.parse_args())

    main(args)
