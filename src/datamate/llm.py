import re
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LLMConfig:
    model_name: str = "Qwen/Qwen2.5-Coder-7B-Instruct"
    load_in_4bit: bool = False
    load_in_8bit: bool = False
    temperature: float = 0.01
    top_p: float = 0.95
    max_new_tokens: int = 1024
    device: str = "auto"


class LocalLLMClient:
    def __init__(self, config: LLMConfig | None = None) -> None:
        self.config = config or LLMConfig()
        self.model: Any = None
        self.tokenizer: Any = None

    def load_model(self) -> None:
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

        self.tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_name,
            trust_remote_code=True,
        )
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        quant_config = None
        if self.config.load_in_4bit:
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
        elif self.config.load_in_8bit:
            quant_config = BitsAndBytesConfig(load_in_8bit=True)

        torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

        self.model = AutoModelForCausalLM.from_pretrained(
            self.config.model_name,
            quantization_config=quant_config,
            torch_dtype=torch_dtype,
            device_map=self.config.device,
            trust_remote_code=True,
        )
        self.model.eval()

    def generate(self, user_prompt: str, system_prompt: str = "") -> str:
        if self.model is None or self.tokenizer is None:
            self.load_model()

        import torch

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_prompt})

        if hasattr(self.tokenizer, "apply_chat_template") and self.tokenizer.chat_template:
            prompt_text = self.tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )
        else:
            prompt_text = f"{system_prompt}\n\nUser: {user_prompt}\nAssistant:"

        inputs = self.tokenizer(
            prompt_text,
            return_tensors="pt",
            truncation=True,
            max_length=8192,
        )
        if hasattr(self.model, "device"):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=self.config.max_new_tokens,
                temperature=self.config.temperature,
                top_p=self.config.top_p,
                do_sample=self.config.temperature > 0.05,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )

        new_tokens = outputs[0][inputs["input_ids"].shape[1] :]
        generated_text = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return generated_text.strip()

    def extract_python_code(self, text: str) -> str:
        python_block = re.search(r"```(?:python|py)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if python_block:
            return python_block.group(1).strip()
        lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
        return "\n".join(lines).strip()
