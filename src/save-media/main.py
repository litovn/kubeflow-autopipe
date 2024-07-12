import shutil
import os
import argparse


def save_media(input_path: str, output_path: str):
    """
    Save media file to a given path

    :param input_path: Path to the media to save
    :param output_path: Path to output directory where to save the media file
    """
    # 'none' needed to copy the media to the directory where this script is located when tool is run,
    # the copied media will be then containerized with the script to be used in the pipeline
    if output_path == 'none':
        output_path = os.path.dirname(os.path.abspath(__file__))
    shutil.copy(input_path, output_path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input media")
    parser.add_argument("-o", "--output", default='none', help="path to output folder")
    args = vars(parser.parse_args())

    save_media(args['input'], args['output'])
