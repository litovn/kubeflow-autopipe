import shutil
import os
import argparse


def save_video(input_path: str, output_path: str):
    if output_path == 'none':
        output_path = os.path.dirname(os.path.abspath(__file__))
    shutil.copy(input_path, output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input video")
    parser.add_argument("-o", "--output", default='none', help="path to output images")
    args = vars(parser.parse_args())

    save_video(args['input'], args['output'])
