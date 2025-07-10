from transformers import AutoTokenizer, AutoModel

# 下载 ClimateBERT 的 tokenizer 和 model
tokenizer = AutoTokenizer.from_pretrained("climatebert/distilroberta-base-climate-f")
model = AutoModel.from_pretrained("climatebert/distilroberta-base-climate-f")