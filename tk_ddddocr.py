# coding=utf-8
import warnings

warnings.filterwarnings('ignore')
import io
import os
import base64
import json
import pathlib
import onnxruntime
from PIL import Image, ImageChops
import numpy as np
import cv2


onnxruntime.set_default_logger_severity(3)

def png_rgba_black_preprocess(img: Image):
    width = img.width
    height = img.height
    image = Image.new('RGB', size=(width, height), color=(255, 255, 255))
    image.paste(img, (0, 0), mask=img)
    return image


class TuringKillerOcr(object):
    def __init__(self, ocr: bool = True, det: bool = False, old: bool = False, beta: bool = False,
                 use_gpu: bool = False,
                 device_id: int = 0,  import_onnx_path: str = "", charsets_path: str = ""):      
        print("欢迎使用turing_killer，本项目专注图灵仿真测试，由topliu和zhi共同发起，以攻促防，带动行业升级")          
        if not hasattr(Image, 'ANTIALIAS'):
            setattr(Image, 'ANTIALIAS', Image.LANCZOS)
        self.use_import_onnx = False
        self.__word = False
        self.__resize = []
        self.__charset_range = []
        self.__channel = 1
        if import_onnx_path != "":
            det = False
            ocr = False
            self.__graph_path = import_onnx_path
            with open(charsets_path, 'r', encoding="utf-8") as f:
                info = json.loads(f.read())
            self.__charset = info['charset']
            self.__word = info['word']
            self.__resize = info['image']
            self.__channel = info['channel']
            self.use_import_onnx = True
       
        if use_gpu:
            self.__providers = [
                ('CUDAExecutionProvider', {
                    'device_id': device_id,
                    'arena_extend_strategy': 'kNextPowerOfTwo',
                    'cuda_mem_limit': 2 * 1024 * 1024 * 1024,
                    'cudnn_conv_algo_search': 'EXHAUSTIVE',
                    'do_copy_in_default_stream': True,
                }),
            ]
        else:
            self.__providers = [
                'CPUExecutionProvider',
            ]
        if ocr or det or self.use_import_onnx:
            self.__ort_session = onnxruntime.InferenceSession(self.__graph_path, providers=self.__providers)

    def preproc(self, img, input_size, swap=(2, 0, 1)):
        if len(img.shape) == 3:
            padded_img = np.ones((input_size[0], input_size[1], 3), dtype=np.uint8) * 114
        else:
            padded_img = np.ones(input_size, dtype=np.uint8) * 114

        r = min(input_size[0] / img.shape[0], input_size[1] / img.shape[1])
        resized_img = cv2.resize(
            img,
            (int(img.shape[1] * r), int(img.shape[0] * r)),
            interpolation=cv2.INTER_LINEAR,
        ).astype(np.uint8)
        padded_img[: int(img.shape[0] * r), : int(img.shape[1] * r)] = resized_img

        padded_img = padded_img.transpose(swap)
        padded_img = np.ascontiguousarray(padded_img, dtype=np.float32)
        return padded_img, r

    def demo_postprocess(self, outputs, img_size, p6=False):
        grids = []
        expanded_strides = []

        if not p6:
            strides = [8, 16, 32]
        else:
            strides = [8, 16, 32, 64]

        hsizes = [img_size[0] // stride for stride in strides]
        wsizes = [img_size[1] // stride for stride in strides]

        for hsize, wsize, stride in zip(hsizes, wsizes, strides):
            xv, yv = np.meshgrid(np.arange(wsize), np.arange(hsize))
            grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
            grids.append(grid)
            shape = grid.shape[:2]
            expanded_strides.append(np.full((*shape, 1), stride))

        grids = np.concatenate(grids, 1)
        expanded_strides = np.concatenate(expanded_strides, 1)
        outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
        outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides

        return outputs

    def multiclass_nms_class_agnostic(self, boxes, scores, nms_thr, score_thr):
        """Multiclass NMS implemented in Numpy. Class-agnostic version."""
        cls_inds = scores.argmax(1)
        cls_scores = scores[np.arange(len(cls_inds)), cls_inds]

        valid_score_mask = cls_scores > score_thr
        if valid_score_mask.sum() == 0:
            return None
        
        valid_scores = cls_scores[valid_score_mask]
        valid_boxes = boxes[valid_score_mask]
        valid_cls_inds = cls_inds[valid_score_mask]
        
        # NMS logic starts here
        x1 = valid_boxes[:, 0]
        y1 = valid_boxes[:, 1]
        x2 = valid_boxes[:, 2]
        y2 = valid_boxes[:, 3]

        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = valid_scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            ovr = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(ovr <= nms_thr)[0]
            order = order[inds + 1]
        # NMS logic ends here

        if keep:
            dets = np.concatenate(
                [valid_boxes[keep], valid_scores[keep, None], valid_cls_inds[keep, None]], 1
            )
        return dets

    def detection(self, image_bytes):
        img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)

        im, ratio = self.preproc(img, (416, 416))
        ort_inputs = {self.__ort_session.get_inputs()[0].name: im[None, :, :, :]}
        output = self.__ort_session.run(None, ort_inputs)
        predictions = self.demo_postprocess(output[0], (416, 416))[0]
        boxes = predictions[:, :4]
        scores = predictions[:, 4:5] * predictions[:, 5:]

        boxes_xyxy = np.ones_like(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.
        boxes_xyxy /= ratio

        pred = self.multiclass_nms_class_agnostic(boxes_xyxy, scores, nms_thr=0.45, score_thr=0.1)
        try:
            final_boxes = pred[:, :4].tolist()
            result = []
            for b in final_boxes:
                if b[0] < 0:
                    x_min = 0
                else:
                    x_min = int(b[0])
                if b[1] < 0:
                    y_min = 0
                else:
                    y_min = int(b[1])
                if b[2] > img.shape[1]:
                    x_max = int(img.shape[1])
                else:
                    x_max = int(b[2])
                if b[3] > img.shape[0]:
                    y_max = int(img.shape[0])
                else:
                    y_max = int(b[3])
                result.append([x_min, y_min, x_max, y_max])
        except Exception as e:
            return []
        return result


    def classification(self, img, png_fix: bool = False, probability=False):        
        if not isinstance(img, (bytes, str, pathlib.PurePath, Image.Image)):
            raise TypeError("未知图片类型")
        if isinstance(img, bytes):
            image = Image.open(io.BytesIO(img))
        elif isinstance(img, Image.Image):
            image = img.copy()
        elif isinstance(img, str):
            img_data = base64.b64decode(img_base64)       
            image = Image.open(io.BytesIO(img_data))
        else:
            assert isinstance(img, pathlib.PurePath)
            image = Image.open(img)
        if not self.use_import_onnx:
            image = image.resize((int(image.size[0] * (64 / image.size[1])), 64), Image.ANTIALIAS).convert('L')
        else:
            if self.__resize[0] == -1:
                if self.__word:
                    image = image.resize((self.__resize[1], self.__resize[1]), Image.ANTIALIAS)
                else:
                    image = image.resize((int(image.size[0] * (self.__resize[1] / image.size[1])), self.__resize[1]),
                                         Image.ANTIALIAS)
            else:
                image = image.resize((self.__resize[0], self.__resize[1]), Image.ANTIALIAS)
            if self.__channel == 1:
                image = image.convert('L')
            else:
                if png_fix:
                    image = png_rgba_black_preprocess(image)
                else:
                    image = image.convert('RGB')
        image = np.array(image).astype(np.float32)
        image = np.expand_dims(image, axis=0) / 255.
        if not self.use_import_onnx:
            image = (image - 0.5) / 0.5
        else:
            if self.__channel == 1:
                image = (image - 0.456) / 0.224
            else:
                image = (image - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
                image = image[0]
                image = image.transpose((2, 0, 1))

        ort_inputs = {'input1': np.array([image]).astype(np.float32)}
        ort_outs = self.__ort_session.run(None, ort_inputs)
        result = []

        last_item = 0

        if self.__word:
            for item in ort_outs[1]:
                result.append(self.__charset[item])
            return ''.join(result)
        else:
            if not self.use_import_onnx:
                # 概率输出仅限于使用官方模型
                if probability:
                    ort_outs = ort_outs[0]
                    ort_outs = np.exp(ort_outs) / np.sum(np.exp(ort_outs))
                    ort_outs_sum = np.sum(ort_outs, axis=2)
                    ort_outs_probability = np.empty_like(ort_outs)
                    for i in range(ort_outs.shape[0]):
                        ort_outs_probability[i] = ort_outs[i] / ort_outs_sum[i]
                    ort_outs_probability = np.squeeze(ort_outs_probability).tolist()
                    result = {}
                    if len(self.__charset_range) == 0:
                        # 返回全部
                        result['charsets'] = self.__charset
                        result['probability'] = ort_outs_probability
                    else:
                        result['charsets'] = self.__charset_range
                        probability_result_index = []
                        for item in self.__charset_range:
                            if item in self.__charset:
                                probability_result_index.append(self.__charset.index(item))
                            else:
                                # 未知字符
                                probability_result_index.append(-1)
                        probability_result = []
                        for item in ort_outs_probability:
                            probability_result.append([item[i] if i != -1 else -1 for i in probability_result_index ])
                        result['probability'] = probability_result
                    return result
                else:
                    last_item = 0
                    argmax_result = np.squeeze(np.argmax(ort_outs[0], axis=2))
                    for item in argmax_result:
                        if item == last_item:
                            continue
                        else:
                            last_item = item
                        if item != 0:
                            result.append(self.__charset[item])
                    return ''.join(result)

            else:
                last_item = 0
                for item in ort_outs[0][0]:
                    if item == last_item:
                        continue
                    else:
                        last_item = item
                    if item != 0:
                        result.append(self.__charset[item])
                return ''.join(result)

    

 