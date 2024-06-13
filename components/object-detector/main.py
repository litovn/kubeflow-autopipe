import onnxruntime
import cv2
import argparse
import os
import numpy as np

from postprocess import *

from aisprint.annotations import annotation
from aisprint.onnx_inference import load_and_inference


def post_processing(image_source, detections):
    STRIDES = [8, 16, 32]
    XYSCALE = [1.2, 1.1, 1.05]
    ANCHORS = get_anchors()
    STRIDES = np.array(STRIDES)

    original_image_size = image_source.shape[:2]
    input_size = 416

    pred_bbox = postprocess_bbbox(detections, ANCHORS, STRIDES, XYSCALE)
    # bboxes = postprocess_boxes(pred_bbox, original_image_size, input_size, 0.25)
    bboxes = postprocess_boxes(pred_bbox, (416, 416), input_size, 0.25)
    bboxes = nms(bboxes, 0.213, method='nms')
    # image = draw_bbox(image_source, bboxes)
    image = alternative_draw_bbox(image_source, bboxes)
    
    return image
    

@annotation({'component_name': {'name': 'object-detector'},
            'partitionable_model': {'onnx_file': 'yolov4.onnx'}
            })
def main(args):
    onnx_model_path = args['onnx_file']
    session = onnxruntime.InferenceSession(onnx_model_path)

    image_path = args['input']
    image_source = cv2.imread(image_path)

    # preprocess
    image_resized = cv2.resize(image_source, (416, 416))
    img_in = cv2.cvtColor(image_resized, cv2.COLOR_BGR2RGB)
    img_in = img_in.astype(np.float32)
    img_in = np.expand_dims(img_in, axis=0)
    img_in /= 255.0

    input_name = session.get_inputs()[0].name

    input_dict = {input_name: img_in, "image_source": image_source}
    input_dict['keep'] = False

    return_dict, detections = load_and_inference(onnx_model_path, input_dict)

    # post_processing
    image = post_processing(return_dict["image_source"], detections)
    
    cv2.imwrite(args['output'] + ".jpg", image)


if __name__ == '__main__':
    
    # construct the argument parser and parse the arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input", required=True, help="path to input image")
    parser.add_argument("-o", "--output", help="path to output images")
    parser.add_argument("-y", "--onnx_file", default="onnx/yolov4.onnx", help="complete path to the ONNX model")
    args = vars(parser.parse_args())

    main(args)

