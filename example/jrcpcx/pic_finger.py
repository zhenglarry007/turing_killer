import hashlib
import numpy as np
from PIL import Image

class PicFinger:
    HASH_SIZE = 16

    def __init__(self, source):
        """
        初始化图片指纹
        :param source: 可以是 numpy 数组（二值化矩阵），也可以是图片路径或 PIL Image 对象
        """
        if isinstance(source, np.ndarray):
            if source.size != self.HASH_SIZE * self.HASH_SIZE:
                raise ValueError(f"length of hashValue must be {self.HASH_SIZE * self.HASH_SIZE}")
            self.binaryzation_matrix = source.flatten()
        elif isinstance(source, list):
            self.binaryzation_matrix = np.array(source, dtype=np.uint8)
        else:
            if isinstance(source, str):
                img = Image.open(source)
            elif isinstance(source, Image.Image):
                img = source
            else:
                raise ValueError("Unsupported source type. Must be image path, PIL Image, list or numpy array.")
            self.binaryzation_matrix = self._hash_value(img)

    def get_hash_code(self):
        """
        获取压缩指纹的 MD5 (16进制大写字符串)
        """
        compact_data = self.compact()
        md5_hash = hashlib.md5(compact_data).hexdigest()
        return md5_hash.upper()

    def get_binaryzation_matrix(self):
        return self.binaryzation_matrix

    def _hash_value(self, img):
        """
        计算图片的二值化哈希数组
        """
        # 1. 缩放图像到指定尺寸 (16x16)
        img_resized = img.resize((self.HASH_SIZE, self.HASH_SIZE), Image.Resampling.LANCZOS)
        
        # 2. 转为灰度图像
        img_gray = img_resized.convert('L')
        
        # 获取像素数据并转为 numpy 数组
        pixels = np.array(img_gray).flatten()
        
        # 3. 计算均值
        mean_val = np.mean(pixels)
        
        # 4. 二值化处理
        # 大于等于均值为 1，小于为 0
        binary_matrix = (pixels >= mean_val).astype(np.uint8)
        return binary_matrix

    def compact(self):
        """
        指纹数据按位压缩 (每 8 个 bit 压缩为 1 个 byte)
        """
        return self._compact_array(self.binaryzation_matrix)

    @staticmethod
    def _compact_array(hash_value):
        result_len = (len(hash_value) + 7) >> 3
        result = bytearray(result_len)
        
        b = 0
        for i in range(len(hash_value)):
            if (i & 7) == 0:
                b = 0
            
            if hash_value[i] == 1:
                b |= 1 << (i & 7)
            elif hash_value[i] != 0:
                raise ValueError("invalid hashValue, every element must be 0 or 1")
                
            if (i & 7) == 7 or i == len(hash_value) - 1:
                result[i >> 3] = b
                
        return bytes(result)

    @classmethod
    def create_from_compact(cls, compact_value):
        """
        从压缩格式指纹创建 PicFinger 对象
        """
        uncompacted = cls._uncompact_array(compact_value)
        return cls(uncompacted)

    @staticmethod
    def _uncompact_array(compact_value):
        """
        压缩格式的指纹解压缩
        """
        result_len = len(compact_value) << 3
        result = np.zeros(result_len, dtype=np.uint8)
        
        for i in range(result_len):
            byte_idx = i >> 3
            bit_offset = i & 7
            if (compact_value[byte_idx] & (1 << bit_offset)) == 0:
                result[i] = 0
            else:
                result[i] = 1
        return result

    def __str__(self):
        return self.to_string(multi_line=True)

    def to_string(self, multi_line=True):
        chars = []
        for i, b in enumerate(self.binaryzation_matrix):
            chars.append('1' if b == 1 else '0')
            if multi_line and (i + 1) % self.HASH_SIZE == 0:
                chars.append('\n')
        return "".join(chars)

    def __eq__(self, other):
        if isinstance(other, PicFinger):
            return np.array_equal(self.binaryzation_matrix, other.binaryzation_matrix)
        return False

    def compare(self, other):
        """
        比较指纹相似度
        :param other: PicFinger 对象或 PIL Image 或 图片路径
        :return: 相似度 (0.0 ~ 1.0)
        """
        if not isinstance(other, PicFinger):
            other = PicFinger(other)
            
        if len(self.binaryzation_matrix) != len(other.binaryzation_matrix):
            raise ValueError("length of hashValue is mismatch")
            
        same_count = np.sum(self.binaryzation_matrix == other.binaryzation_matrix)
        return float(same_count) / len(self.binaryzation_matrix)

    def compare_compact(self, compact_value):
        """
        与指定的压缩格式指纹比较相似度
        """
        other_finger = self.create_from_compact(compact_value)
        return self.compare(other_finger)

    @classmethod
    def compare_images(cls, img1_path, img2_path):
        """
        直接比较两张图片的相似度
        """
        fp1 = cls(img1_path)
        fp2 = cls(img2_path)
        return fp1.compare(fp2)

if __name__ == "__main__":
    import os
    
    # 创建一个测试环境
    print("=== 测试 Python 版 PicFinger ===")
    
    # 这里我们生成两张纯色图片来做简单测试
    # 实际应用中可以换成真实的图片路径
    img1 = Image.new('RGB', (100, 100), color = 'red')
    img2 = Image.new('RGB', (100, 100), color = 'darkred')
    img3 = Image.new('RGB', (100, 100), color = 'blue')
    
    # 测试指纹生成
    fp1 = PicFinger(img1)
    fp2 = PicFinger(img2)
    fp3 = PicFinger(img3)
    
    print("\n[指纹 MD5 哈希值]")
    print(f"img1 (red): {fp1.get_hash_code()}")
    print(f"img2 (darkred): {fp2.get_hash_code()}")
    print(f"img3 (blue): {fp3.get_hash_code()}")
    
    print("\n[相似度比较]")
    sim_1_2 = fp1.compare(fp2)
    print(f"img1(红) 与 img2(暗红) 的相似度: {sim_1_2 * 100:.2f}%")
    
    sim_1_3 = fp1.compare(fp3)
    print(f"img1(红) 与 img3(蓝) 的相似度: {sim_1_3 * 100:.2f}%")
    
    # 测试压缩与解压
    print("\n[测试压缩与解压]")
    compact_data = fp1.compact()
    print(f"压缩后的字节长度: {len(compact_data)} bytes (原始: 256 bytes)")
    
    fp_restored = PicFinger.create_from_compact(compact_data)
    print(f"解压后是否与原指纹相同: {fp1 == fp_restored}")
    
    # 打印其中一个指纹矩阵的样子
    print("\n[img1 二值化矩阵 (16x16)]")
    print(fp1.to_string(multi_line=True))