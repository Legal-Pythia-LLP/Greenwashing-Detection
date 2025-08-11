import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))  # 把 docs 加进 sys.path

from app.core.rules_engine import RuleEngine

def run_test():
    engine = RuleEngine()  # 读取 data_files/rules.json
    sample_text = """
    Our product is eco-friendly and 100% natural.
    We aim to achieve net zero emissions by 2030.
    """
    result = engine.analyze(sample_text)
    print("Test input:", sample_text)
    print("Analysis result:", result)

if __name__ == "__main__":
    run_test()
