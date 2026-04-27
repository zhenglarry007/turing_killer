import torch
from PIL import Image
# 1. 关键修改：导入 AutoModelForVision2Seq 和 AutoProcessor
from transformers import AutoModelForVision2Seq, AutoProcessor

MODEL_ID = "Qwen/Qwen3-VL-8B-Instruct"

print("正在加载 processor...")
# 2. 使用 AutoProcessor 替代 AutoTokenizer
processor = AutoProcessor.from_pretrained(MODEL_ID, trust_remote_code=True)

print("正在加载模型（使用 INT4 量化）...")
# 3. 关键修改：使用 AutoModelForVision2Seq 替代 AutoModelForCausalLM
model = AutoModelForVision2Seq.from_pretrained(
    MODEL_ID,
    device_map="auto",
    trust_remote_code=True,
    load_in_4bit=True,
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4"
).eval()

print("加载图像...")
image = Image.open("/Users/larryzheng/Downloads/code/turing_killer/demo/pic/0001.png").convert("RGB")

print("构建多模态输入...")
# 4. 使用 processor 构建输入，这是推荐的标准方式
messages = [
    {
        "role": "user",
        "content": [
            {"type": "image", "image": image},
            {"type": "text", "text": "识别图中所有汉字，按从左到右、从上到下顺序输出。不要任何解释，只返回文字。"}
        ]
    }
]

# 5. 使用 processor 处理输入
text_input = processor.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
inputs = processor(text=text_input, images=[image], return_tensors="pt", padding=True).to(model.device)

print("开始推理...")
# 6. 使用模型自带的 generate 方法进行推理
generated_ids = model.generate(**inputs, max_new_tokens=256, do_sample=False)

# 7. 解码并输出结果
response = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]
# 清理输出，只保留助手回复的部分
response = response.split("assistant\n")[1].strip()

print("\n✅ OCR 结果：")
print(response)